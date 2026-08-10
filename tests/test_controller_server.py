from __future__ import annotations

import http.cookiejar
import json
import queue
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import soundfile as sf

from filmrecorder.controller_server import ControllerServer


class ControllerServerTests(unittest.TestCase):
    def setUp(self):
        self.commands = queue.Queue()
        self.temp = tempfile.TemporaryDirectory()
        web = Path(self.temp.name)
        (web / "index.html").write_text("<html>remote</html>", encoding="utf-8")
        self.audio_path = Path(self.temp.name) / "take.wav"
        sf.write(self.audio_path, np.zeros((480, 4), dtype=np.float32), 48000, subtype="PCM_24")
        self.server = ControllerServer(
            command_sink=self.commands.put,
            state_provider=lambda: {"recording": False, "scene": "12A", "version": "test", "project": "Unit Test"},
            token="123456",
            web_root=web,
            take_provider=lambda: [{"id": "take.wav", "file": "take.wav", "scene": "12A", "take": 1}],
            take_resolver=lambda take_id: self.audio_path if take_id == "take.wav" else (_ for _ in ()).throw(FileNotFoundError()),
        )
        self.server.start(host="127.0.0.1", port=0)
        self.base = f"http://127.0.0.1:{self.server.port}"

    def tearDown(self):
        self.server.stop()
        self.temp.cleanup()

    def request(self, path, method="GET", token=None, payload=None, opener=None):
        data = None
        headers = {}
        if token is not None:
            headers["X-FilmRec-Token"] = token
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        if opener is None:
            response_ctx = urllib.request.urlopen(req, timeout=2.0)
        else:
            response_ctx = opener.open(req, timeout=2.0)
        with response_ctx as response:
            return response.status, response.read(), response.headers

    def json_request(self, *args, **kwargs):
        status, raw, headers = self.request(*args, **kwargs)
        return status, json.loads(raw.decode("utf-8")), headers

    def test_health_is_public(self):
        status, body, _ = self.json_request("/health")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])

    def test_web_root_is_public(self):
        status, raw, headers = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(b"remote", raw)
        self.assertIn("text/html", headers.get("Content-Type", ""))


    def test_embedded_web_fallback_without_web_root(self):
        self.server.stop()
        self.server = ControllerServer(
            command_sink=self.commands.put,
            state_provider=lambda: {"recording": False, "scene": "12A", "version": "test", "project": "Unit Test"},
            token="123456",
            web_root=None,
        )
        self.server.start(host="127.0.0.1", port=0)
        self.base = f"http://127.0.0.1:{self.server.port}"
        status, raw, headers = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(b"FILMSET RECORDER", raw)
        self.assertIn("text/html", headers.get("Content-Type", ""))
        status, raw, headers = self.request("/app.js")
        self.assertEqual(status, 200)
        self.assertIn(b"api/status", raw)
        self.assertIn("javascript", headers.get("Content-Type", ""))

    def test_status_requires_token(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.json_request("/status")
        self.assertEqual(caught.exception.code, 401)
        status, body, _ = self.json_request("/status", token="123456")
        self.assertEqual(status, 200)
        self.assertEqual(body["scene"], "12A")

    def test_browser_pairing_cookie_authorizes_status(self):
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        status, body, _ = self.json_request("/api/pair", method="POST", payload={"pin": "123456"}, opener=opener)
        self.assertEqual(status, 200)
        self.assertTrue(body["paired"])
        status, body, _ = self.json_request("/api/status", opener=opener)
        self.assertEqual(status, 200)
        self.assertEqual(body["scene"], "12A")

    def test_bad_pairing_pin_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.json_request("/api/pair", method="POST", payload={"pin": "999999"})
        self.assertEqual(caught.exception.code, 401)

    def test_command_delivery_and_deduplication(self):
        payload = {"command": "record", "request_id": "abc"}
        status, body, _ = self.json_request("/command", method="POST", token="123456", payload=payload)
        self.assertEqual(status, 202)
        self.assertEqual(self.commands.get(timeout=1.0)["command"], "record")
        status, body, _ = self.json_request("/command", method="POST", token="123456", payload=payload)
        self.assertEqual(status, 200)
        self.assertTrue(body["duplicate"])
        with self.assertRaises(queue.Empty):
            self.commands.get(timeout=0.1)

    def test_take_list_and_phone_audio_stream_require_auth(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.json_request("/api/takes")
        self.assertEqual(caught.exception.code, 401)
        status, body, _ = self.json_request("/api/takes", token="123456")
        self.assertEqual(status, 200)
        self.assertEqual(body["takes"][0]["file"], "take.wav")
        status, raw, headers = self.request("/api/audio?id=take.wav", token="123456")
        self.assertEqual(status, 200)
        self.assertEqual(raw[:4], b"RIFF")
        self.assertIn("audio/wav", headers.get("Content-Type", ""))


if __name__ == "__main__":
    unittest.main()
