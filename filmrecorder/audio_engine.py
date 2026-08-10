from __future__ import annotations

import logging
import os
import queue
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import sounddevice as sd
import soundfile as sf

from .session import ProjectSession

LOGGER = logging.getLogger("filmsetrecorder.audio")


@dataclass
class AudioDevice:
    index: int
    name: str
    max_input_channels: int
    max_output_channels: int
    default_samplerate: float
    hostapi: int
    default_low_input_latency: float = 0.0
    default_low_output_latency: float = 0.0


class AudioEngine:
    """Conservative multichannel recorder with pre-roll and crash-safe finalization.

    The PortAudio input callback never performs disk I/O. It only calculates
    lightweight peak data and pushes copied blocks into a bounded queue. A
    dedicated writer thread writes 24-bit PCM WAV data to a .partial.wav file.
    The file is atomically renamed to its final name only after a clean stop.
    """

    def __init__(self, meter_callback: Optional[Callable[[list[float]], None]] = None):
        self.meter_callback = meter_callback
        self.stream: Optional[sd.InputStream] = None
        self.device_index: Optional[int] = None
        self.sample_rate = 48000
        self.channels = 4
        self.blocksize = 512
        self.pre_roll_seconds = 5.0

        self._recording = False
        self._record_started_monotonic = 0.0
        self._last_record_elapsed = 0.0
        self._final_path: Optional[Path] = None
        self._partial_path: Optional[Path] = None
        self._write_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=4096)
        self._writer_thread: Optional[threading.Thread] = None
        self._writer_stop = threading.Event()
        self._writer_done = threading.Event()
        self._writer_error: Optional[str] = None
        self._finalized_path: Optional[Path] = None
        self._frames_recorded = 0
        self._xrun_count = 0
        self._dropped_blocks = 0
        self._lock = threading.RLock()

        self._pre_roll: deque[np.ndarray] = deque()
        self._pre_roll_max_blocks = 0
        self._callback_state_lock = threading.Lock()
        self._armed_mask = np.ones(self.channels, dtype=bool)
        self._record_mask = np.ones(self.channels, dtype=bool)

        self._play_stream: Optional[sd.OutputStream] = None
        self._play_file: Optional[sf.SoundFile] = None
        self._play_lock = threading.RLock()
        self._playing = False

    @staticmethod
    def devices() -> list[AudioDevice]:
        results: list[AudioDevice] = []
        for i, dev in enumerate(sd.query_devices()):
            results.append(AudioDevice(
                index=i,
                name=str(dev["name"]),
                max_input_channels=int(dev["max_input_channels"]),
                max_output_channels=int(dev["max_output_channels"]),
                default_samplerate=float(dev["default_samplerate"]),
                hostapi=int(dev["hostapi"]),
                default_low_input_latency=float(dev.get("default_low_input_latency", 0.0)),
                default_low_output_latency=float(dev.get("default_low_output_latency", 0.0)),
            ))
        return results

    @staticmethod
    def hostapis():
        return sd.query_hostapis()

    @property
    def recording(self) -> bool:
        with self._lock:
            return self._recording

    @property
    def playing(self) -> bool:
        with self._play_lock:
            return self._playing

    @property
    def frames_recorded(self) -> int:
        with self._lock:
            return self._frames_recorded

    @property
    def elapsed_seconds(self) -> float:
        with self._lock:
            if self._recording and self._record_started_monotonic > 0:
                return max(0.0, time.monotonic() - self._record_started_monotonic)
            return max(0.0, self._last_record_elapsed)

    @property
    def file_duration_seconds(self) -> float:
        return self.frames_recorded / float(self.sample_rate or 1)

    @property
    def xrun_count(self) -> int:
        with self._lock:
            return self._xrun_count

    @property
    def dropped_blocks(self) -> int:
        with self._lock:
            return self._dropped_blocks

    @property
    def writer_queue_percent(self) -> float:
        maxsize = float(self._write_queue.maxsize or 1)
        return min(100.0, max(0.0, self._write_queue.qsize() / maxsize * 100.0))

    @property
    def writer_error(self) -> Optional[str]:
        with self._lock:
            return self._writer_error

    @property
    def finalized_path(self) -> Optional[Path]:
        with self._lock:
            return self._finalized_path

    def configure(
        self,
        device_index: int,
        channels: int = 4,
        sample_rate: int = 48000,
        blocksize: int = 512,
        pre_roll_seconds: float = 5.0,
    ) -> None:
        if self.stream is not None:
            raise RuntimeError("Stop monitoring before changing audio settings.")
        dev = sd.query_devices(device_index)
        max_in = int(dev["max_input_channels"])
        if max_in < 1:
            raise ValueError("Selected device has no input channels.")

        channels = max(1, min(int(channels), max_in))
        sample_rate = int(sample_rate)
        blocksize = max(64, int(blocksize))
        sd.check_input_settings(
            device=device_index,
            channels=channels,
            samplerate=sample_rate,
            dtype="float32",
        )

        self.device_index = int(device_index)
        self.channels = channels
        self.sample_rate = sample_rate
        self.blocksize = blocksize
        self.pre_roll_seconds = max(0.0, min(30.0, float(pre_roll_seconds)))
        self._armed_mask = np.ones(self.channels, dtype=bool)
        self._record_mask = self._armed_mask.copy()
        self._resize_pre_roll()
        LOGGER.info(
            "Configured input device=%s channels=%s sample_rate=%s blocksize=%s pre_roll=%.1f",
            self.device_index,
            self.channels,
            self.sample_rate,
            self.blocksize,
            self.pre_roll_seconds,
        )

    def _resize_pre_roll(self) -> None:
        if self.blocksize <= 0 or self.sample_rate <= 0:
            self._pre_roll_max_blocks = 0
        else:
            self._pre_roll_max_blocks = int(
                max(0.0, self.pre_roll_seconds) * self.sample_rate / self.blocksize
            ) + 2
        with self._callback_state_lock:
            previous = list(self._pre_roll)
            self._pre_roll = deque(previous[-self._pre_roll_max_blocks:], maxlen=self._pre_roll_max_blocks or None)
            if self._pre_roll_max_blocks == 0:
                self._pre_roll.clear()

    def set_armed_channels(self, armed: list[bool]) -> None:
        values = list(bool(x) for x in armed[: self.channels])
        if len(values) < self.channels:
            values.extend([True] * (self.channels - len(values)))
        mask = np.asarray(values, dtype=bool)
        with self._lock:
            if self._recording:
                raise RuntimeError("Track arming cannot be changed while recording.")
            self._armed_mask = mask

    def start_monitoring(self) -> None:
        if self.stream is not None:
            return
        if self.device_index is None:
            raise RuntimeError("No audio input device selected.")
        self._resize_pre_roll()
        self.stream = sd.InputStream(
            device=self.device_index,
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            blocksize=self.blocksize,
            callback=self._audio_callback,
        )
        self.stream.start()
        LOGGER.info("Input monitoring started")

    def stop_monitoring(self) -> None:
        if self.recording:
            self.stop_recording()
        if self.stream is not None:
            try:
                self.stream.stop()
            finally:
                self.stream.close()
                self.stream = None
        with self._callback_state_lock:
            self._pre_roll.clear()
        LOGGER.info("Input monitoring stopped")

    def _audio_callback(self, indata, frames, time_info, status) -> None:
        if status:
            with self._lock:
                self._xrun_count += 1
            LOGGER.warning("PortAudio input status: %s", status)

        peaks = np.max(np.abs(indata), axis=0)
        db = 20.0 * np.log10(np.maximum(peaks, 1e-8))
        if self.meter_callback is not None:
            self.meter_callback([float(v) for v in db])

        block = indata.copy()
        with self._callback_state_lock:
            if self._pre_roll_max_blocks > 0:
                self._pre_roll.append(block)
            if self._recording:
                try:
                    self._write_queue.put_nowait(block)
                except queue.Full:
                    with self._lock:
                        self._dropped_blocks += 1
                        self._xrun_count += 1

    def _drain_write_queue(self) -> None:
        while True:
            try:
                self._write_queue.get_nowait()
                self._write_queue.task_done()
            except queue.Empty:
                return

    def start_recording(self, final_path: Path) -> Path:
        if self.recording:
            raise RuntimeError("A recording is already in progress.")
        if self.stream is None:
            self.start_monitoring()

        final_path = Path(final_path)
        final_path.parent.mkdir(parents=True, exist_ok=True)
        partial_path = ProjectSession.partial_path(final_path)
        if final_path.exists() or partial_path.exists():
            raise FileExistsError(f"Recording target already exists: {final_path.name}")

        self.stop_playback()
        self._drain_write_queue()
        self._writer_stop.clear()
        self._writer_done.clear()

        # Atomically snapshot pre-roll and enable live queueing relative to the
        # audio callback. A callback block is therefore either in the pre-roll
        # snapshot or in the live write queue, never duplicated or skipped at
        # the transition boundary.
        with self._callback_state_lock:
            pre_roll_blocks = list(self._pre_roll)
            with self._lock:
                self._frames_recorded = 0
                self._writer_error = None
                self._finalized_path = None
                self._final_path = final_path
                self._partial_path = partial_path
                self._record_mask = self._armed_mask.copy()
                self._record_started_monotonic = time.monotonic()
                self._last_record_elapsed = 0.0
                self._recording = True

        self._writer_thread = threading.Thread(
            target=self._writer_loop,
            args=(final_path, partial_path, pre_roll_blocks, self._record_mask.copy()),
            name="FilmRecWriter",
            daemon=True,
        )
        self._writer_thread.start()
        LOGGER.info("Recording started: %s", final_path)
        return final_path

    @staticmethod
    def _apply_record_mask(block: np.ndarray, mask: np.ndarray) -> np.ndarray:
        if bool(np.all(mask)):
            return block
        output = block.copy()
        output[:, ~mask] = 0.0
        return output


    @staticmethod
    def _sync_wav_header(wav: sf.SoundFile) -> None:
        """Flush audio and ask libsndfile to refresh the WAV header.

        libsndfile normally writes final length fields on close. Updating the
        header periodically makes an interrupted .partial.wav readable up to
        the most recent sync point. The private binding call is guarded so a
        future python-soundfile implementation can fall back to flush-only.
        """
        wav.flush()
        try:
            command_update_header_now = 0x1060
            sf._snd.sf_command(wav._file, command_update_header_now, sf._ffi.NULL, 0)
            wav.flush()
        except Exception:
            LOGGER.debug("Periodic WAV header refresh is unavailable", exc_info=True)

    def _writer_loop(
        self,
        final_path: Path,
        partial_path: Path,
        pre_roll_blocks: list[np.ndarray],
        record_mask: np.ndarray,
    ) -> None:
        last_flush = time.monotonic()
        error: Optional[Exception] = None
        try:
            with sf.SoundFile(
                str(partial_path),
                mode="w",
                samplerate=self.sample_rate,
                channels=self.channels,
                format="WAV",
                subtype="PCM_24",
            ) as wav:
                for block in pre_roll_blocks:
                    output = self._apply_record_mask(block, record_mask)
                    wav.write(output)
                    with self._lock:
                        self._frames_recorded += len(output)

                while not self._writer_stop.is_set() or not self._write_queue.empty():
                    try:
                        block = self._write_queue.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    try:
                        output = self._apply_record_mask(block, record_mask)
                        wav.write(output)
                        with self._lock:
                            self._frames_recorded += len(output)
                    finally:
                        self._write_queue.task_done()

                    now = time.monotonic()
                    if now - last_flush >= 3.0:
                        self._sync_wav_header(wav)
                        last_flush = now
                self._sync_wav_header(wav)

            os.replace(partial_path, final_path)
            with self._lock:
                self._finalized_path = final_path
            LOGGER.info("Recording finalized: %s", final_path)
        except Exception as exc:
            error = exc
            LOGGER.exception("Recorder writer failed")
            with self._lock:
                self._writer_error = str(exc)
        finally:
            with self._callback_state_lock:
                with self._lock:
                    if self._record_started_monotonic > 0 and self._last_record_elapsed <= 0:
                        self._last_record_elapsed = max(0.0, time.monotonic() - self._record_started_monotonic)
                    self._recording = False
            self._writer_done.set()
            if error is not None:
                LOGGER.error("Partial recording retained at %s", partial_path)

    def stop_recording(self, timeout: float = 20.0) -> Optional[Path]:
        with self._callback_state_lock:
            with self._lock:
                was_recording = self._recording
                if self._record_started_monotonic > 0:
                    self._last_record_elapsed = max(0.0, time.monotonic() - self._record_started_monotonic)
                self._recording = False
        if not was_recording and self._writer_thread is None:
            return self.finalized_path

        self._writer_stop.set()
        thread = self._writer_thread
        if thread is not None:
            thread.join(timeout=timeout)
            if thread.is_alive():
                with self._lock:
                    self._writer_error = "Disk writer did not finish before the safety timeout."
                LOGGER.error("Writer thread timed out")
            else:
                self._writer_thread = None

        error = self.writer_error
        if error:
            raise RuntimeError(error)
        return self.finalized_path

    def play_file(self, path: Path, output_device: Optional[int] = None) -> None:
        if self.recording:
            raise RuntimeError("Playback is disabled while recording.")
        self.stop_playback()
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(path)

        handle = sf.SoundFile(str(path), mode="r")
        try:
            device_info = sd.query_devices(output_device, "output") if output_device is not None else sd.query_devices(kind="output")
            max_out = int(device_info["max_output_channels"])
            output_channels = 2 if max_out >= 2 else 1
            if max_out < 1:
                raise RuntimeError("Selected output device has no playback channels.")

            def callback(outdata, frames, time_info, status):
                if status:
                    LOGGER.warning("PortAudio playback status: %s", status)
                data = handle.read(frames, dtype="float32", always_2d=True)
                count = len(data)
                outdata.fill(0.0)
                if count:
                    mono = np.mean(data, axis=1, dtype=np.float32)
                    if output_channels == 1:
                        outdata[:count, 0] = mono
                    else:
                        outdata[:count, 0] = mono
                        outdata[:count, 1] = mono
                if count < frames:
                    raise sd.CallbackStop

            def finished():
                try:
                    handle.close()
                except Exception:
                    pass
                with self._play_lock:
                    self._playing = False
                    self._play_file = None

            stream = sd.OutputStream(
                device=output_device,
                samplerate=int(handle.samplerate),
                channels=output_channels,
                dtype="float32",
                blocksize=1024,
                callback=callback,
                finished_callback=finished,
            )
            with self._play_lock:
                self._play_file = handle
                self._play_stream = stream
                self._playing = True
            stream.start()
            LOGGER.info("Playback started: %s", path)
        except Exception:
            handle.close()
            raise

    def stop_playback(self) -> None:
        with self._play_lock:
            stream = self._play_stream
            handle = self._play_file
            self._play_stream = None
            self._play_file = None
            self._playing = False
        if stream is not None:
            try:
                stream.stop()
            except Exception:
                pass
            try:
                stream.close()
            except Exception:
                pass
        if handle is not None:
            try:
                handle.close()
            except Exception:
                pass

    def reset_counters(self) -> None:
        with self._lock:
            self._xrun_count = 0
            self._dropped_blocks = 0
