from __future__ import annotations

import json
import logging
import mimetypes
import secrets
import threading
import time
from collections import deque
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable

import numpy as np
import soundfile as sf
import struct
from urllib.parse import parse_qs, unquote, urlparse

from .embedded_web import EMBEDDED_WEB

LOGGER = logging.getLogger("filmsetrecorder.remote")


class ControllerServer:
    """Local HTTP server used by both the ESP32 remote and browser clients.

    ESP32 clients authenticate with the six-digit recorder PIN in the
    ``X-FilmRec-Token`` header. Browser clients pair once with that PIN and
    receive an HttpOnly session cookie for subsequent requests.
    """

    def __init__(
        self,
        command_sink: Callable[[dict], None],
        state_provider: Callable[[], dict],
        token: str,
        web_root: Path | None = None,
        take_provider: Callable[[], list[dict]] | None = None,
        take_resolver: Callable[[str], Path] | None = None,
    ):
        self.command_sink = command_sink
        self.state_provider = state_provider
        self.token = str(token)
        self.web_root = Path(web_root) if web_root else None
        self.take_provider = take_provider
        self.take_resolver = take_resolver
        self.httpd: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.port: int | None = None
        self._seen_ids: deque[str] = deque(maxlen=256)
        self._seen_lock = threading.Lock()
        self._sessions: dict[str, dict] = {}
        self._sessions_lock = threading.Lock()

    def _new_session(self, ip: str, user_agent: str) -> str:
        token = secrets.token_urlsafe(32)
        now = time.time()
        with self._sessions_lock:
            self._sessions[token] = {
                "created": now,
                "last_seen": now,
                "ip": ip,
                "user_agent": user_agent[:240],
            }
            # Keep the in-memory session table bounded.
            if len(self._sessions) > 64:
                oldest = sorted(self._sessions.items(), key=lambda item: item[1]["last_seen"])[:16]
                for key, _ in oldest:
                    self._sessions.pop(key, None)
        return token

    def _touch_session(self, token: str) -> bool:
        now = time.time()
        with self._sessions_lock:
            info = self._sessions.get(token)
            if not info:
                return False
            # Browser pairings expire after 24 hours of inactivity.
            if now - float(info.get("last_seen", now)) > 86400:
                self._sessions.pop(token, None)
                return False
            info["last_seen"] = now
            return True

    def connected_clients(self) -> list[dict]:
        now = time.time()
        clients: list[dict] = []
        with self._sessions_lock:
            stale: list[str] = []
            for key, info in self._sessions.items():
                age = now - float(info.get("last_seen", now))
                if age > 86400:
                    stale.append(key)
                    continue
                if age <= 30:
                    clients.append(
                        {
                            "ip": info.get("ip", ""),
                            "user_agent": info.get("user_agent", ""),
                            "last_seen_seconds": round(age, 1),
                        }
                    )
            for key in stale:
                self._sessions.pop(key, None)
        return clients

    def revoke_browser_sessions(self) -> None:
        with self._sessions_lock:
            self._sessions.clear()

    def start(self, host: str = "0.0.0.0", port: int = 8765) -> None:
        parent = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "FilmSetRecorderRemote/0.3"

            def _session_cookie(self) -> str:
                raw = self.headers.get("Cookie", "")
                try:
                    jar = cookies.SimpleCookie()
                    jar.load(raw)
                    morsel = jar.get("filmrec_session")
                    return morsel.value if morsel else ""
                except Exception:
                    return ""

            def _authorized(self) -> bool:
                header_token = self.headers.get("X-FilmRec-Token", "")
                if header_token and secrets.compare_digest(header_token, parent.token):
                    return True
                session_token = self._session_cookie()
                return bool(session_token and parent._touch_session(session_token))

            def _send_json(self, code: int, obj: dict, extra_headers: dict[str, str] | None = None) -> None:
                body = json.dumps(obj, separators=(",", ":")).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Referrer-Policy", "no-referrer")
                if extra_headers:
                    for key, value in extra_headers.items():
                        self.send_header(key, value)
                self.end_headers()
                self.wfile.write(body)

            def _send_file(self, path: Path) -> None:
                try:
                    data = path.read_bytes()
                except OSError:
                    return self._send_json(404, {"error": "not found"})
                mime, _ = mimetypes.guess_type(str(path))
                self.send_response(200)
                self.send_header("Content-Type", mime or "application/octet-stream")
                self.send_header("Content-Length", str(len(data)))
                if path.suffix.lower() in {".html", ".json"}:
                    self.send_header("Cache-Control", "no-cache")
                else:
                    self.send_header("Cache-Control", "public, max-age=3600")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Referrer-Policy", "no-referrer")
                self.end_headers()
                self.wfile.write(data)

            def _send_embedded(self, relative: str) -> bool:
                asset = EMBEDDED_WEB.get(relative)
                if not asset:
                    return False
                mime, data = asset
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(data)))
                if relative.endswith((".html", ".json", ".webmanifest")):
                    self.send_header("Cache-Control", "no-cache")
                else:
                    self.send_header("Cache-Control", "public, max-age=3600")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Referrer-Policy", "no-referrer")
                self.end_headers()
                self.wfile.write(data)
                return True

            def _serve_web(self, request_path: str) -> None:
                relative = "index.html" if request_path in ("", "/") else unquote(request_path.lstrip("/"))
                # Reject traversal before consulting either the filesystem or embedded assets.
                if not relative or relative.startswith(("/", "\\")) or ".." in Path(relative).parts:
                    return self._send_json(403, {"error": "forbidden"})

                # Prefer external files during development. In packaged builds, PyInstaller
                # may relocate data into _internal; if they are missing for any reason,
                # the exact same UI is compiled into embedded_web.py as a guaranteed fallback.
                if parent.web_root:
                    root = parent.web_root.resolve()
                    candidate = (root / relative).resolve()
                    try:
                        candidate.relative_to(root)
                    except ValueError:
                        return self._send_json(403, {"error": "forbidden"})
                    if candidate.is_dir():
                        candidate = candidate / "index.html"
                    if candidate.is_file():
                        return self._send_file(candidate)

                if self._send_embedded(relative):
                    return
                return self._send_json(404, {"error": "not found"})

            def _send_phone_audio(self, path: Path) -> None:
                """Stream a browser-friendly stereo 16-bit WAV mix without creating a temp file."""
                try:
                    handle = sf.SoundFile(str(path), mode="r")
                except Exception as exc:
                    return self._send_json(404, {"error": f"Audio unavailable: {exc}"})
                try:
                    frames = int(handle.frames)
                    sample_rate = int(handle.samplerate)
                    channels = 2
                    bits = 16
                    block_align = channels * bits // 8
                    data_size = frames * block_align
                    if data_size > 0xFFFFFFFF - 44:
                        return self._send_json(413, {"error": "Take is too large for browser WAV streaming."})
                    header = (
                        b"RIFF" + struct.pack("<I", 36 + data_size) + b"WAVE"
                        + b"fmt " + struct.pack("<IHHIIHH", 16, 1, channels, sample_rate, sample_rate * block_align, block_align, bits)
                        + b"data" + struct.pack("<I", data_size)
                    )
                    self.send_response(200)
                    self.send_header("Content-Type", "audio/wav")
                    self.send_header("Content-Length", str(len(header) + data_size))
                    self.send_header("Content-Disposition", f'inline; filename="{path.stem}_phone_mix.wav"')
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("X-Content-Type-Options", "nosniff")
                    self.end_headers()
                    self.wfile.write(header)
                    while True:
                        data = handle.read(8192, dtype="float32", always_2d=True)
                        if not len(data):
                            break
                        mono = np.mean(data, axis=1, dtype=np.float32)
                        mono = np.clip(mono, -1.0, 1.0)
                        pcm = (mono * 32767.0).astype("<i2")
                        stereo = np.column_stack((pcm, pcm)).astype("<i2", copy=False)
                        self.wfile.write(stereo.tobytes())
                except (BrokenPipeError, ConnectionResetError):
                    pass
                finally:
                    handle.close()

            def do_GET(self) -> None:
                parsed = urlparse(self.path)
                path = parsed.path
                if path == "/health":
                    return self._send_json(200, {"ok": True, "service": "FilmSetRecorder"})
                if path in ("/status", "/api/status"):
                    if not self._authorized():
                        return self._send_json(401, {"error": "unauthorized", "pairing_required": True})
                    state = parent.state_provider()
                    state["connected_web_clients"] = len(parent.connected_clients())
                    return self._send_json(200, state)
                if path == "/api/info":
                    state = parent.state_provider()
                    return self._send_json(
                        200,
                        {
                            "service": "FilmSet Recorder",
                            "version": state.get("version", ""),
                            "project": state.get("project", ""),
                            "pairing_required": not self._authorized(),
                        },
                    )
                if path == "/api/takes":
                    if not self._authorized():
                        return self._send_json(401, {"error": "unauthorized", "pairing_required": True})
                    try:
                        takes = parent.take_provider() if parent.take_provider else []
                        return self._send_json(200, {"takes": takes})
                    except Exception as exc:
                        return self._send_json(500, {"error": str(exc)})
                if path == "/api/audio":
                    if not self._authorized():
                        return self._send_json(401, {"error": "unauthorized", "pairing_required": True})
                    try:
                        take_id = parse_qs(parsed.query).get("id", [""])[0]
                        if not parent.take_resolver:
                            raise FileNotFoundError("Take resolver unavailable.")
                        return self._send_phone_audio(parent.take_resolver(take_id))
                    except Exception as exc:
                        return self._send_json(404, {"error": str(exc)})
                return self._serve_web(path)

            def do_POST(self) -> None:
                parsed = urlparse(self.path)
                path = parsed.path
                try:
                    length = min(int(self.headers.get("Content-Length", "0")), 16384)
                    payload = json.loads(self.rfile.read(length) or b"{}")
                    if not isinstance(payload, dict):
                        raise ValueError("Request body must be a JSON object.")
                except Exception as exc:
                    return self._send_json(400, {"error": str(exc)})

                if path == "/api/pair":
                    submitted = str(payload.get("pin", "")).strip()
                    if not secrets.compare_digest(submitted, parent.token):
                        time.sleep(0.15)
                        return self._send_json(401, {"error": "Incorrect pairing code."})
                    session_token = parent._new_session(
                        self.client_address[0] if self.client_address else "",
                        self.headers.get("User-Agent", ""),
                    )
                    cookie = (
                        f"filmrec_session={session_token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=86400"
                    )
                    return self._send_json(200, {"paired": True}, {"Set-Cookie": cookie})

                if path == "/api/unpair":
                    session_token = self._session_cookie()
                    if session_token:
                        with parent._sessions_lock:
                            parent._sessions.pop(session_token, None)
                    expired = "filmrec_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0"
                    return self._send_json(200, {"paired": False}, {"Set-Cookie": expired})

                if not self._authorized():
                    return self._send_json(401, {"error": "unauthorized", "pairing_required": True})

                if path not in ("/command", "/api/command"):
                    return self._send_json(404, {"error": "not found"})

                try:
                    request_id = str(payload.get("request_id", "")).strip()
                    if request_id:
                        with parent._seen_lock:
                            if request_id in parent._seen_ids:
                                return self._send_json(200, {"accepted": True, "duplicate": True})
                            parent._seen_ids.append(request_id)
                    parent.command_sink(payload)
                    return self._send_json(202, {"accepted": True})
                except Exception as exc:
                    return self._send_json(400, {"error": str(exc)})

            def log_message(self, fmt, *args) -> None:
                return

        class RecorderHTTPServer(ThreadingHTTPServer):
            daemon_threads = True
            allow_reuse_address = True

        self.httpd = RecorderHTTPServer((host, int(port)), Handler)
        self.port = int(self.httpd.server_address[1])
        self.thread = threading.Thread(target=self.httpd.serve_forever, name="FilmRecRemote", daemon=True)
        self.thread.start()
        LOGGER.info("Remote control server started on %s:%s", host, self.port)

    def stop(self) -> None:
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None
            self.port = None
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None
        with self._sessions_lock:
            self._sessions.clear()
        LOGGER.info("Remote control server stopped")
