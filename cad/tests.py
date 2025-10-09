"""Unit tests for the CAD offset API."""
from __future__ import annotations

import json
import struct

from django.test import Client, TestCase
from django.core.files.uploadedfile import SimpleUploadedFile


class OffsetViewTests(TestCase):
    def setUp(self) -> None:  # pragma: no cover - Django hook
        self.client = Client()

    def test_offset_with_json_payload(self) -> None:
        payload = {
            "points": [
                {"position": [0, 0, 0], "normal": [0, 0, 1]},
                {"position": [1, 1, 1], "normal": [1, 0, 0]},
            ]
        }
        upload = SimpleUploadedFile(
            "sample.json", json.dumps(payload).encode("utf-8"), content_type="application/json"
        )

        response = self.client.post("/offset", {"offset": "2.5", "file": upload})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("offset_points", data)
        self.assertAlmostEqual(data["offset_points"][0][2], 2.5)
        self.assertAlmostEqual(data["offset_points"][1][0], 1 + 2.5)
        self.assertNotIn("source_stl", data)

    def test_offset_with_csv_payload(self) -> None:
        csv_content = "0 0 0 0 0 1\n1 1 1 1 0 0"
        upload = SimpleUploadedFile("sample.txt", csv_content.encode("utf-8"))

        response = self.client.post("/offset", {"offset": "1", "file": upload})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["offset_points"]), 2)
        self.assertAlmostEqual(data["offset_points"][0][2], 1)
        self.assertAlmostEqual(data["offset_points"][1][0], 2)

    def test_offset_with_ascii_stl_payload(self) -> None:
        stl_content = """solid ascii\nfacet normal 0 0 1\n outer loop\n  vertex 0 0 0\n  vertex 1 0 0\n  vertex 0 1 0\n endloop\nendfacet\nendsolid\n"""
        upload = SimpleUploadedFile("triangle.stl", stl_content.encode("utf-8"), content_type="model/stl")

        response = self.client.post("/offset", {"offset": "0.5", "file": upload})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["offset_points"]), 3)
        self.assertAlmostEqual(data["offset_points"][0][2], 0.5)
        self.assertIn("source_stl", data)
        self.assertIn("offset_stl", data)
        self.assertIn("solid source_mesh", data["source_stl"])
        self.assertIn("solid offset_mesh", data["offset_stl"])

    def test_offset_with_binary_stl_payload(self) -> None:
        header = b"Binary STL".ljust(80, b" ")
        triangle_count = 1
        triangle_header = struct.pack("<I", triangle_count)
        triangle_body = struct.pack(
            "<12fH",
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0,
        )
        upload = SimpleUploadedFile(
            "triangle-binary.stl", header + triangle_header + triangle_body, content_type="model/stl"
        )

        response = self.client.post("/offset", {"offset": "0.25", "file": upload})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["offset_points"]), 3)
        self.assertAlmostEqual(data["offset_points"][0][2], 0.25)
        self.assertIn("source_stl", data)
        self.assertIn("offset_stl", data)

    def test_missing_file_returns_error(self) -> None:
        response = self.client.post("/offset", {"offset": "1"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_invalid_offset_returns_error(self) -> None:
        payload = {"points": [{"position": [0, 0, 0], "normal": [0, 0, 1]}]}
        upload = SimpleUploadedFile("sample.json", json.dumps(payload).encode("utf-8"))

        response = self.client.post("/offset", {"offset": "abc", "file": upload})

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())
