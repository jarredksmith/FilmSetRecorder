from __future__ import annotations

import csv
import json
import os
import shutil
import struct
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable

import soundfile as sf

from .utils import safe_filename_component


@dataclass
class TakeMetadata:
    file: str
    project: str
    roll: str
    scene: str
    take: int
    recorded_at: str
    duration_seconds: float
    sample_rate: int
    channels: int
    track_names: list[str] = field(default_factory=list)
    armed_tracks: list[bool] = field(default_factory=list)
    circle: bool = False
    notes: str = ""
    frame_rate: str = "23.976"
    xruns: int = 0
    dropped_blocks: int = 0
    pre_roll_seconds: float = 0.0
    app_version: str = ""
    recovered: bool = False


class ProjectSession:
    REPORT_FIELDS = [
        "recorded_at", "roll", "scene", "take", "circle", "file",
        "duration_seconds", "sample_rate", "channels", "frame_rate",
        "track_names", "notes", "xruns", "dropped_blocks", "recovered",
    ]

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).expanduser().resolve()
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir = self.project_dir / ".filmset"
        self.state_dir.mkdir(parents=True, exist_ok=True)

    @property
    def project_name(self) -> str:
        return self.project_dir.name or "Untitled Project"

    @property
    def report_path(self) -> Path:
        return self.project_dir / "sound_report.csv"

    def roll_dir(self, roll: str) -> Path:
        name = safe_filename_component(roll, "ROLL")
        path = self.project_dir / name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def allocate_take_path(self, roll: str, scene: str, take: int) -> Path:
        roll_name = safe_filename_component(roll, "ROLL")
        scene_name = safe_filename_component(scene, "SCENE")
        stem = f"{roll_name}_{scene_name}_T{int(take):03d}"
        folder = self.project_dir / roll_name
        candidate = folder / f"{stem}.wav"
        if not candidate.exists() and not self.partial_path(candidate).exists():
            return candidate
        counter = 2
        while True:
            candidate = folder / f"{stem}_{counter:02d}.wav"
            if not candidate.exists() and not self.partial_path(candidate).exists():
                return candidate
            counter += 1

    @staticmethod
    def partial_path(final_path: Path) -> Path:
        final_path = Path(final_path)
        return final_path.with_name(f"{final_path.stem}.partial.wav")

    def metadata_path(self, audio_path: Path) -> Path:
        return Path(audio_path).with_suffix(".json")

    def write_take_metadata(self, audio_path: Path, metadata: TakeMetadata) -> Path:
        target = self.metadata_path(audio_path)
        temp = target.with_suffix(".json.tmp")
        temp.write_text(json.dumps(asdict(metadata), indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(temp, target)
        self.rebuild_sound_report()
        return target

    def read_take_metadata(self, audio_path: Path) -> dict:
        path = self.metadata_path(audio_path)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def update_take_metadata(self, audio_path: Path, **changes) -> None:
        path = self.metadata_path(audio_path)
        if not path.exists():
            return
        data = self.read_take_metadata(audio_path)
        if not data:
            return
        data.update(changes)
        temp = path.with_suffix(".json.tmp")
        temp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(temp, path)
        self.rebuild_sound_report()

    def iter_metadata_files(self) -> Iterable[Path]:
        for path in sorted(self.project_dir.rglob("*.json")):
            if self.state_dir in path.parents:
                continue
            yield path


    def list_takes(self, limit: int | None = None) -> list[dict]:
        """Return completed takes newest-first for desktop and remote browsers.

        Each item uses a project-relative WAV path as its opaque-ish ``id``.
        The resolver validates that id before it can be used for playback.
        """
        items: list[dict] = []
        seen: set[Path] = set()
        for meta_path in self.iter_metadata_files():
            audio_path = meta_path.with_suffix(".wav")
            if not audio_path.exists():
                continue
            try:
                data = self.read_take_metadata(audio_path)
                info = sf.info(str(audio_path))
            except Exception:
                continue
            try:
                rel = audio_path.resolve().relative_to(self.project_dir).as_posix()
            except ValueError:
                continue
            seen.add(audio_path.resolve())
            items.append({
                "id": rel,
                "file": audio_path.name,
                "roll": str(data.get("roll", audio_path.parent.name)),
                "scene": str(data.get("scene", "")),
                "take": int(data.get("take", 0) or 0),
                "circle": bool(data.get("circle", False)),
                "notes": str(data.get("notes", "")),
                "recorded_at": str(data.get("recorded_at", "")),
                "duration_seconds": float(data.get("duration_seconds", float(info.frames) / float(info.samplerate or 1)) or 0.0),
                "sample_rate": int(data.get("sample_rate", info.samplerate) or info.samplerate),
                "channels": int(data.get("channels", info.channels) or info.channels),
                "recovered": bool(data.get("recovered", False)),
            })

        # Include valid WAVs that predate metadata or were imported into the project.
        for audio_path in self.project_dir.rglob("*.wav"):
            resolved = audio_path.resolve()
            if resolved in seen or audio_path.name.endswith(".partial.wav") or self.state_dir in audio_path.parents:
                continue
            try:
                rel = resolved.relative_to(self.project_dir).as_posix()
                info = sf.info(str(audio_path))
            except Exception:
                continue
            items.append({
                "id": rel, "file": audio_path.name, "roll": audio_path.parent.name,
                "scene": "", "take": 0, "circle": False, "notes": "",
                "recorded_at": datetime.fromtimestamp(audio_path.stat().st_mtime).isoformat(timespec="seconds"),
                "duration_seconds": float(info.frames) / float(info.samplerate or 1),
                "sample_rate": int(info.samplerate), "channels": int(info.channels), "recovered": False,
            })

        items.sort(key=lambda item: str(item.get("recorded_at", "")), reverse=True)
        return items[: max(0, int(limit))] if limit is not None else items

    def relative_take_id(self, audio_path: Path) -> str:
        path = Path(audio_path).resolve()
        try:
            return path.relative_to(self.project_dir).as_posix()
        except ValueError as exc:
            raise ValueError("Take is outside the active project.") from exc

    def resolve_take_id(self, take_id: str) -> Path:
        """Resolve a playlist id to a completed WAV inside the project."""
        raw = str(take_id or "").strip().replace("\\", "/")
        if not raw or raw.startswith("/") or ".." in Path(raw).parts:
            raise ValueError("Invalid take id.")
        candidate = (self.project_dir / raw).resolve()
        try:
            candidate.relative_to(self.project_dir)
        except ValueError as exc:
            raise ValueError("Take is outside the active project.") from exc
        if candidate.suffix.lower() != ".wav" or candidate.name.endswith(".partial.wav") or not candidate.is_file():
            raise FileNotFoundError("Take audio is not available.")
        return candidate

    def rebuild_sound_report(self) -> Path:
        rows: list[dict] = []
        for path in self.iter_metadata_files():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            rows.append(data)
        rows.sort(key=lambda item: str(item.get("recorded_at", "")))
        temp = self.report_path.with_suffix(".csv.tmp")
        with temp.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.REPORT_FIELDS, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                item = dict(row)
                item["circle"] = "YES" if bool(item.get("circle")) else ""
                item["recovered"] = "YES" if bool(item.get("recovered")) else ""
                names = item.get("track_names", [])
                if isinstance(names, list):
                    item["track_names"] = " | ".join(str(x) for x in names)
                item["notes"] = str(item.get("notes", "")).replace("\r", " ").replace("\n", " / ")
                writer.writerow({field: item.get(field, "") for field in self.REPORT_FIELDS})
        os.replace(temp, self.report_path)
        return self.report_path

    def disk_free_bytes(self) -> int:
        return int(shutil.disk_usage(self.project_dir).free)

    def estimated_record_seconds(self, sample_rate: int, channels: int, bytes_per_sample: int = 3) -> float:
        bytes_per_second = max(1, int(sample_rate) * max(1, int(channels)) * int(bytes_per_sample))
        return self.disk_free_bytes() / float(bytes_per_second)

    def ensure_writable(self) -> None:
        probe = self.state_dir / ".write_test"
        try:
            probe.write_text("ok", encoding="ascii")
            probe.unlink(missing_ok=True)
        except Exception as exc:
            raise OSError(f"Project folder is not writable: {self.project_dir}") from exc


    @staticmethod
    def repair_pcm_wav_header(path: Path) -> bool:
        """Repair RIFF/data lengths using the physical file size.

        This is intentionally conservative and only touches standard RIFF/WAVE
        files with a recognizable fmt and data chunk. It is used for unfinished
        PCM recordings after an interrupted process.
        """
        path = Path(path)
        file_size = path.stat().st_size
        if file_size < 44 or file_size - 8 > 0xFFFFFFFF:
            return False
        with path.open("r+b") as handle:
            header = handle.read(12)
            if len(header) != 12 or header[:4] != b"RIFF" or header[8:12] != b"WAVE":
                return False
            block_align = 0
            offset = 12
            data_size_offset = None
            data_start = None
            while offset + 8 <= file_size:
                handle.seek(offset)
                chunk_header = handle.read(8)
                if len(chunk_header) != 8:
                    break
                chunk_id = chunk_header[:4]
                chunk_size = struct.unpack("<I", chunk_header[4:8])[0]
                payload = offset + 8
                if chunk_id == b"fmt " and chunk_size >= 16:
                    handle.seek(payload + 12)
                    raw = handle.read(2)
                    if len(raw) == 2:
                        block_align = struct.unpack("<H", raw)[0]
                if chunk_id == b"data":
                    data_size_offset = offset + 4
                    data_start = payload
                    break
                next_offset = payload + chunk_size + (chunk_size & 1)
                if next_offset <= offset or next_offset > file_size:
                    break
                offset = next_offset

            if data_size_offset is None or data_start is None or data_start > file_size:
                return False
            physical_data = file_size - data_start
            if block_align > 0:
                physical_data -= physical_data % block_align
            if physical_data < 0 or physical_data > 0xFFFFFFFF:
                return False
            repaired_size = data_start + physical_data
            handle.seek(data_size_offset)
            handle.write(struct.pack("<I", int(physical_data)))
            handle.seek(4)
            handle.write(struct.pack("<I", int(repaired_size - 8)))
            if repaired_size < file_size:
                handle.truncate(repaired_size)
            handle.flush()
            os.fsync(handle.fileno())
        return True

    def find_partial_recordings(self) -> list[Path]:
        return sorted(self.project_dir.rglob("*.partial.wav"))

    def recover_partial(self, partial_path: Path) -> Path:
        partial_path = Path(partial_path)
        try:
            self.repair_pcm_wav_header(partial_path)
        except Exception:
            pass
        info = sf.info(str(partial_path))
        if info.frames <= 0:
            raise ValueError(f"Partial file contains no audio frames: {partial_path.name}")
        stem = partial_path.name
        if stem.endswith(".partial.wav"):
            stem = stem[:-len(".partial.wav")]
        candidate = partial_path.with_name(f"{stem}_RECOVERED.wav")
        counter = 2
        while candidate.exists():
            candidate = partial_path.with_name(f"{stem}_RECOVERED_{counter:02d}.wav")
            counter += 1
        os.replace(partial_path, candidate)
        recovered = TakeMetadata(
            file=candidate.name,
            project=self.project_name,
            roll=candidate.parent.name,
            scene="RECOVERED",
            take=0,
            recorded_at=datetime.now().isoformat(timespec="seconds"),
            duration_seconds=float(info.frames) / float(info.samplerate or 1),
            sample_rate=int(info.samplerate),
            channels=int(info.channels),
            track_names=[f"Input {i + 1}" for i in range(int(info.channels))],
            armed_tracks=[True] * int(info.channels),
            notes="Recovered from an unfinished recording after an interrupted session.",
            recovered=True,
        )
        self.write_take_metadata(candidate, recovered)
        return candidate
