from __future__ import annotations

import json
import queue
import time
import unittest
import urllib.error
import urllib.request

from filmrecorder.controller_server import ControllerServer


class ControllerServerTests(unittest.TestCase):
    def setUp(self):
        self.commands = queue.Queue()
        self.server = ControllerServer(
            command_sink=self.commands.put,
            state_provider=lambda: {"recording": False, "scene": "12A"},
            token="123456",
        )
        self.server.start(host="127.0.0.1", port=0)
        self.base = f"http://127.0.0.1:{self.server.port}"

    def tearDown(self):
        self.server.stop()

    def request(self, path, method="GET", token=None, payload=None):
        data = None
        headers = {}
        if token is not None:
            headers["X-FilmRec-Token"] = token
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=2.0) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def test_health_is_public(self):
        status, body = self.request("/health")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])

    def test_status_requires_token(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.request("/status")
        self.assertEqual(caught.exception.code, 401)
        status, body = self.request("/status", token="123456")
        self.assertEqual(status, 200)
        self.assertEqual(body["scene"], "12A")

    def test_command_delivery_and_deduplication(self):
        payload = {"command": "record", "request_id": "abc"}
        status, body = self.request("/command", method="POST", token="123456", payload=payload)
        self.assertEqual(status, 202)
        self.assertEqual(self.commands.get(timeout=1.0)["command"], "record")
        status, body = self.request("/command", method="POST", token="123456", payload=payload)
        self.assertEqual(status, 200)
        self.assertTrue(body["duplicate"])
        with self.assertRaises(queue.Empty):
            self.commands.get(timeout=0.1)


if __name__ == "__main__":
    unittest.main()
