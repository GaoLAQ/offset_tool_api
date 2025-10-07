"""Views for handling CAD offset calculations."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable, List, Tuple

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


@dataclass
class PointData:
    """Represents a point and its surface normal."""

    position: Tuple[float, float, float]
    normal: Tuple[float, float, float]


class CADParseError(ValueError):
    """Raised when the uploaded CAD data cannot be parsed."""


def _load_json_points(data: str) -> Iterable[PointData]:
    payload = json.loads(data)
    points = payload["points"] if isinstance(payload, dict) else payload
    for idx, item in enumerate(points):
        try:
            position = tuple(float(value) for value in item["position"])
            normal = tuple(float(value) for value in item["normal"])
        except (KeyError, TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise CADParseError(f"Invalid point definition at index {idx}.") from exc
        if len(position) != 3 or len(normal) != 3:
            raise CADParseError(f"Point at index {idx} must include 3D position and normal.")
        yield PointData(position=position, normal=normal)


def _load_csv_points(data: str) -> Iterable[PointData]:
    points: List[PointData] = []
    for line_number, line in enumerate(data.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        raw_values = [value for value in stripped.replace(";", " ").replace(",", " ").split() if value]
        if len(raw_values) != 6:
            raise CADParseError(
                "Each line must contain 6 numeric values: x y z nx ny nz. "
                f"Problem found on line {line_number}."
            )
        try:
            position = tuple(float(value) for value in raw_values[:3])
            normal = tuple(float(value) for value in raw_values[3:])
        except ValueError as exc:
            raise CADParseError(f"Non-numeric value on line {line_number}.") from exc
        points.append(PointData(position=position, normal=normal))
    return points


def parse_cad_points(uploaded_file) -> List[PointData]:
    """Parse an uploaded CAD file and return a list of points with normals."""

    data = uploaded_file.read()
    if isinstance(data, bytes):
        try:
            text_data = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CADParseError("Uploaded file must be UTF-8 encoded text.") from exc
    else:
        text_data = str(data)

    text_data = text_data.strip()
    if not text_data:
        raise CADParseError("Uploaded file is empty.")

    # Try JSON first and fall back to a whitespace / comma separated format.
    try:
        return list(_load_json_points(text_data))
    except json.JSONDecodeError:
        return list(_load_csv_points(text_data))


def offset_points(points: Iterable[PointData], offset: float) -> List[Tuple[float, float, float]]:
    """Apply an offset along the normal for each point."""

    result: List[Tuple[float, float, float]] = []
    for point in points:
        nx, ny, nz = point.normal
        magnitude = (nx**2 + ny**2 + nz**2) ** 0.5
        if magnitude == 0:
            raise CADParseError("Normal vector cannot be zero.")
        unit_normal = (nx / magnitude, ny / magnitude, nz / magnitude)
        px, py, pz = point.position
        result.append(
            (
                px + unit_normal[0] * offset,
                py + unit_normal[1] * offset,
                pz + unit_normal[2] * offset,
            )
        )
    return result


@csrf_exempt
@require_http_methods(["POST"])
def offset_view(request: HttpRequest) -> JsonResponse:
    """Handle CAD file uploads and return offset coordinates."""

    uploaded_file = request.FILES.get("file")
    if uploaded_file is None:
        return JsonResponse({"error": "Missing CAD file in 'file' field."}, status=400)

    try:
        offset_value = float(request.POST.get("offset", ""))
    except ValueError:
        return JsonResponse({"error": "Offset must be a numeric value."}, status=400)

    try:
        points = parse_cad_points(uploaded_file)
        offset_positions = offset_points(points, offset_value)
    except CADParseError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse({"offset_points": offset_positions})
