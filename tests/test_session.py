from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import numpy as np
import soundfile as sf

from filmrecorder.session import ProjectSession, TakeMetadata
from filmrecorder.utils import safe_filename_component


class SessionTests(unittest.TestCase):
    def test_safe_filename_component(self):
        self.assertEqual(safe_filename_component("24B / pickup", "SCENE"), "24B_pickup")
        self.assertEqual(safe_filename_component("", "SCENE"), "SCENE")

    def test_allocate_take_path_never_overwrites(self):
        with tempfile.TemporaryDirectory() as temp:
            session = ProjectSession(Path(temp))
            first = session.allocate_take_path("A001", "24B", 3)
            first.parent.mkdir(parents=True, exist_ok=True)
            first.write_bytes(b"existing")
            second = session.allocate_take_path("A001", "24B", 3)
            self.assertNotEqual(first, second)
            self.assertTrue(second.name.endswith("_02.wav"))

    def test_metadata_builds_sound_report(self):
        with tempfile.TemporaryDirectory() as temp:
            session = ProjectSession(Path(temp))
            audio = session.allocate_take_path("A001", "1", 1)
            audio.parent.mkdir(parents=True, exist_ok=True)
            sf.write(audio, np.zeros((480, 2), dtype=np.float32), 48000, subtype="PCM_24")
            meta = TakeMetadata(
                file=audio.name,
                project=session.project_name,
                roll="A001",
                scene="1",
                take=1,
                recorded_at=datetime.now().isoformat(timespec="seconds"),
                duration_seconds=0.01,
                sample_rate=48000,
                channels=2,
                track_names=["Boom", "Lav"],
                armed_tracks=[True, True],
                circle=True,
                notes="Good take",
            )
            session.write_take_metadata(audio, meta)
            self.assertTrue(session.report_path.exists())
            report = session.report_path.read_text(encoding="utf-8-sig")
            self.assertIn("Boom | Lav", report)
            self.assertIn("Good take", report)
            data = json.loads(audio.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertTrue(data["circle"])


    def test_repair_pcm_wav_header_after_interruption(self):
        with tempfile.TemporaryDirectory() as temp:
            session = ProjectSession(Path(temp))
            path = Path(temp) / "broken.partial.wav"
            samples = np.zeros((9600, 2), dtype=np.float32)
            sf.write(path, samples, 48000, subtype="PCM_24")
            raw = bytearray(path.read_bytes())
            data_at = raw.find(b"data")
            self.assertGreater(data_at, 0)
            raw[4:8] = (36).to_bytes(4, "little")
            raw[data_at + 4:data_at + 8] = (0).to_bytes(4, "little")
            path.write_bytes(raw)
            self.assertTrue(session.repair_pcm_wav_header(path))
            info = sf.info(str(path))
            self.assertEqual(info.frames, 9600)

    def test_recover_partial_wav(self):
        with tempfile.TemporaryDirectory() as temp:
            session = ProjectSession(Path(temp))
            final = session.allocate_take_path("A001", "TEST", 1)
            partial = session.partial_path(final)
            partial.parent.mkdir(parents=True, exist_ok=True)
            sf.write(partial, np.zeros((4800, 1), dtype=np.float32), 48000, subtype="PCM_24")
            recovered = session.recover_partial(partial)
            self.assertTrue(recovered.exists())
            self.assertFalse(partial.exists())
            self.assertIn("RECOVERED", recovered.name)
            self.assertTrue(recovered.with_suffix(".json").exists())

    def test_take_playlist_and_secure_resolver(self):
        with tempfile.TemporaryDirectory() as temp:
            session = ProjectSession(Path(temp))
            audio = session.allocate_take_path("A001", "12A", 2)
            audio.parent.mkdir(parents=True, exist_ok=True)
            sf.write(audio, np.zeros((4800, 4), dtype=np.float32), 48000, subtype="PCM_24")
            meta = TakeMetadata(
                file=audio.name, project=session.project_name, roll="A001", scene="12A", take=2,
                recorded_at="2026-08-09T19:00:00", duration_seconds=0.1, sample_rate=48000, channels=4,
                track_names=["Boom", "Lav A", "Lav B", "Plant"], armed_tracks=[True] * 4, circle=True, notes="Print take",
            )
            session.write_take_metadata(audio, meta)
            takes = session.list_takes()
            self.assertEqual(len(takes), 1)
            self.assertEqual(takes[0]["scene"], "12A")
            self.assertTrue(takes[0]["circle"])
            self.assertEqual(session.resolve_take_id(takes[0]["id"]), audio.resolve())
            with self.assertRaises((ValueError, FileNotFoundError)):
                session.resolve_take_id("../outside.wav")


if __name__ == "__main__":
    unittest.main()
