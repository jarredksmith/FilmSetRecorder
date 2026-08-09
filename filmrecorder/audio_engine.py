from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import sounddevice as sd
import soundfile as sf


@dataclass
class AudioDevice:
    index: int
    name: str
    max_input_channels: int
    max_output_channels: int
    default_samplerate: float
    hostapi: int


class AudioEngine:
    """Small, conservative multichannel recorder engine.

    Audio arrives in PortAudio's callback. The callback never writes to disk;
    it copies blocks into a queue and a dedicated writer thread handles disk IO.
    """

    def __init__(self, meter_callback: Optional[Callable[[list[float]], None]] = None):
        self.meter_callback = meter_callback
        self.stream: Optional[sd.InputStream] = None
        self.device_index: Optional[int] = None
        self.sample_rate = 48000
        self.channels = 4
        self.blocksize = 1024
        self._recording = False
        self._record_path: Optional[Path] = None
        self._write_queue: queue.Queue = queue.Queue(maxsize=512)
        self._writer_thread: Optional[threading.Thread] = None
        self._writer_stop = threading.Event()
        self._frames_recorded = 0
        self._xrun_count = 0
        self._lock = threading.RLock()

    @staticmethod
    def devices() -> list[AudioDevice]:
        results: list[AudioDevice] = []
        for i, dev in enumerate(sd.query_devices()):
            results.append(AudioDevice(
                index=i,
                name=str(dev['name']),
                max_input_channels=int(dev['max_input_channels']),
                max_output_channels=int(dev['max_output_channels']),
                default_samplerate=float(dev['default_samplerate']),
                hostapi=int(dev['hostapi']),
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
    def frames_recorded(self) -> int:
        with self._lock:
            return self._frames_recorded

    @property
    def elapsed_seconds(self) -> float:
        return self.frames_recorded / float(self.sample_rate or 1)

    @property
    def xrun_count(self) -> int:
        with self._lock:
            return self._xrun_count

    def configure(self, device_index: int, channels: int = 4, sample_rate: int = 48000, blocksize: int = 1024):
        if self.stream is not None:
            raise RuntimeError('Stop monitoring before changing audio settings.')
        dev = sd.query_devices(device_index)
        max_in = int(dev['max_input_channels'])
        if max_in < 1:
            raise ValueError('Selected device has no input channels.')
        self.device_index = device_index
        self.channels = max(1, min(int(channels), max_in))
        self.sample_rate = int(sample_rate)
        self.blocksize = int(blocksize)
        sd.check_input_settings(device=device_index, channels=self.channels, samplerate=self.sample_rate, dtype='float32')

    def start_monitoring(self):
        if self.stream is not None:
            return
        if self.device_index is None:
            raise RuntimeError('No audio input device selected.')
        self.stream = sd.InputStream(
            device=self.device_index,
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype='float32',
            blocksize=self.blocksize,
            callback=self._audio_callback,
        )
        self.stream.start()

    def stop_monitoring(self):
        if self.recording:
            self.stop_recording()
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            with self._lock:
                self._xrun_count += 1

        # dBFS peak meters. Keep callback work intentionally small.
        if self.meter_callback is not None:
            peaks = np.max(np.abs(indata), axis=0)
            db = 20.0 * np.log10(np.maximum(peaks, 1e-7))
            self.meter_callback([float(v) for v in db])

        if self.recording:
            try:
                self._write_queue.put_nowait(indata.copy())
            except queue.Full:
                with self._lock:
                    self._xrun_count += 1

    def start_recording(self, path: Path):
        if self.recording:
            return
        if self.stream is None:
            self.start_monitoring()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            self._recording = True
            self._record_path = path
            self._frames_recorded = 0
        self._writer_stop.clear()
        self._writer_thread = threading.Thread(target=self._writer_loop, args=(path,), daemon=True)
        self._writer_thread.start()

    def _writer_loop(self, path: Path):
        try:
            with sf.SoundFile(
                str(path),
                mode='w',
                samplerate=self.sample_rate,
                channels=self.channels,
                format='WAV',
                subtype='PCM_24',
            ) as wav:
                while not self._writer_stop.is_set() or not self._write_queue.empty():
                    try:
                        block = self._write_queue.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    wav.write(block)
                    with self._lock:
                        self._frames_recorded += len(block)
                    self._write_queue.task_done()
        finally:
            with self._lock:
                self._recording = False

    def stop_recording(self):
        if not self.recording:
            return
        with self._lock:
            self._recording = False
        self._writer_stop.set()
        if self._writer_thread:
            self._writer_thread.join(timeout=5.0)
            self._writer_thread = None
        while True:
            try:
                self._write_queue.get_nowait()
                self._write_queue.task_done()
            except queue.Empty:
                break

    def play_file(self, path: Path, output_device: Optional[int] = None):
        data, samplerate = sf.read(str(path), dtype='float32', always_2d=True)
        sd.stop()
        sd.play(data, samplerate=samplerate, device=output_device, blocking=False)

    def stop_playback(self):
        sd.stop()
