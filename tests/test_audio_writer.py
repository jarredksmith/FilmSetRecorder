from __future__ import annotations

import sys
import tempfile
import time
import types
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf

try:
    import sounddevice  # noqa: F401
except ImportError:
    sys.modules["sounddevice"] = types.SimpleNamespace()

from filmrecorder.audio_engine import AudioEngine


class AudioWriterTests(unittest.TestCase):
    def test_pre_roll_live_audio_and_arm_mask(self):
        with tempfile.TemporaryDirectory() as temp:
            engine = AudioEngine()
            engine.sample_rate = 48000
            engine.channels = 4
            engine.blocksize = 512
            engine.pre_roll_seconds = 5.0
            engine._armed_mask = np.asarray([True, True, False, True], dtype=bool)
            engine._record_mask = engine._armed_mask.copy()
            engine._resize_pre_roll()
            engine.stream = object()  # Bypass hardware startup for writer-only test.

            pre_blocks = []
            for index in range(5):
                block = np.full((512, 4), 0.01 * (index + 1), dtype=np.float32)
                pre_blocks.append(block.copy())
                engine._audio_callback(block, 512, None, None)

            output = Path(temp) / "A001_TEST_T001.wav"
            engine.start_recording(output)

            live_blocks = []
            for index in range(7):
                block = np.full((512, 4), 0.1 + 0.01 * index, dtype=np.float32)
                live_blocks.append(block.copy())
                engine._audio_callback(block, 512, None, None)

            final = engine.stop_recording(timeout=5.0)
            self.assertEqual(final, output)
            self.assertTrue(output.exists())
            self.assertFalse(output.with_name("A001_TEST_T001.partial.wav").exists())

            data, sample_rate = sf.read(output, dtype="float32", always_2d=True)
            self.assertEqual(sample_rate, 48000)
            self.assertEqual(data.shape, ((len(pre_blocks) + len(live_blocks)) * 512, 4))
            self.assertLess(float(np.max(np.abs(data[:, 2]))), 1e-6)
            self.assertGreater(float(np.max(np.abs(data[:, 0]))), 0.1)

    def test_periodic_header_sync_produces_readable_open_wav(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sync.partial.wav"
            with sf.SoundFile(path, "w", samplerate=48000, channels=2, format="WAV", subtype="PCM_24") as wav:
                wav.write(np.zeros((2400, 2), dtype=np.float32))
                AudioEngine._sync_wav_header(wav)
                info = sf.info(path)
                self.assertEqual(info.frames, 2400)


if __name__ == "__main__":
    unittest.main()

class AudioRoutingTrimTests(unittest.TestCase):
    def test_track_source_routing_and_digital_trim(self):
        block = np.asarray([[0.10, 0.20], [-0.10, -0.20]], dtype=np.float32)
        mask = np.asarray([True, True], dtype=bool)
        sources = np.asarray([1, 0], dtype=np.int32)
        trims = np.asarray([6.0, -6.0], dtype=np.float32)
        output = AudioEngine._process_record_block(block, mask, sources, trims)
        self.assertEqual(output.shape, (2, 2))
        self.assertAlmostEqual(float(output[0, 0]), 0.20 * (10 ** (6.0 / 20.0)), places=5)
        self.assertAlmostEqual(float(output[0, 1]), 0.10 * (10 ** (-6.0 / 20.0)), places=5)

    def test_record_trim_can_update_while_recording_state_is_true(self):
        engine = AudioEngine()
        engine.channels = 2
        engine._record_trims_db = np.zeros(2, dtype=np.float32)
        engine._recording = True
        engine.set_record_trims_db([3.0, -4.5])
        self.assertEqual([round(x, 1) for x in engine.record_trims_db], [3.0, -4.5])
