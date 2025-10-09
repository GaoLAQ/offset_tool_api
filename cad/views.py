"""Views for handling CAD offset calculations."""
from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from typing import Iterable, List, Tuple

from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
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


def _load_stl_points_text(data: str) -> Iterable[PointData]:
    """Parse an ASCII STL file into a sequence of points with normals."""

    points: List[PointData] = []
    current_normal: Tuple[float, float, float] | None = None

    for line_number, line in enumerate(data.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        tokens = stripped.lower().split()
        if tokens[:2] == ["facet", "normal"]:
            original_parts = stripped.split()
            if len(original_parts) != 5:
                raise CADParseError(
                    "Facet normal must include three numeric components. "
                    f"Problem found on line {line_number}."
                )
            try:
                normal_values = tuple(float(value) for value in original_parts[2:5])
                current_normal = (
                    float(normal_values[0]),
                    float(normal_values[1]),
                    float(normal_values[2]),
                )
            except ValueError as exc:
                raise CADParseError(f"Invalid normal definition on line {line_number}.") from exc
        elif tokens and tokens[0] == "vertex":
            if current_normal is None:
                raise CADParseError(
                    "Encountered vertex before a facet normal definition. "
                    f"Problem found on line {line_number}."
                )
            components = stripped.split()
            if len(components) != 4:
                raise CADParseError(
                    "Vertex definition must include three numeric coordinates. "
                    f"Problem found on line {line_number}."
                )
            try:
                position = tuple(float(value) for value in components[1:4])
            except ValueError as exc:
                raise CADParseError(f"Invalid vertex definition on line {line_number}.") from exc
            points.append(PointData(position=position, normal=current_normal))
        elif tokens and tokens[0] == "endfacet":
            current_normal = None

    if not points:
        raise CADParseError("No vertices were found in the provided STL file.")

    return points


def _load_stl_points_binary(data: bytes) -> Iterable[PointData]:
    """Parse a binary STL file into a sequence of points with normals."""

    if len(data) < 84:
        raise CADParseError("Binary STL file is too small to contain any geometry.")

    triangle_count = struct.unpack_from("<I", data, 80)[0]
    expected_size = 84 + triangle_count * 50
    if len(data) < expected_size:
        raise CADParseError("Binary STL file is truncated and cannot be parsed.")

    offset = 84
    points: List[PointData] = []

    for _ in range(triangle_count):
        normal = struct.unpack_from("<fff", data, offset)
        offset += 12
        for _ in range(3):
            position = struct.unpack_from("<fff", data, offset)
            offset += 12
            points.append(PointData(position=position, normal=normal))
        offset += 2  # Skip attribute byte count

    if not points:
        raise CADParseError("Binary STL file contained no vertices.")

    return points


def parse_cad_points(uploaded_file) -> List[PointData]:
    """Parse an uploaded CAD file and return a list of points with normals."""

    raw_data = uploaded_file.read()
    if isinstance(raw_data, bytes):
        binary_data = raw_data
    else:
        binary_data = str(raw_data).encode("utf-8")

    if not binary_data:
        raise CADParseError("Uploaded file is empty.")

    text_data: str | None
    try:
        text_data = binary_data.decode("utf-8")
    except UnicodeDecodeError:
        text_data = None

    if text_data is not None:
        stripped = text_data.strip()
        if not stripped:
            raise CADParseError("Uploaded file is empty.")

        try:
            return list(_load_json_points(stripped))
        except json.JSONDecodeError:
            pass

        try:
            return list(_load_stl_points_text(stripped))
        except CADParseError:
            pass

        try:
            return list(_load_csv_points(stripped))
        except CADParseError as csv_error:
            raise CADParseError("Unsupported CAD file format. Provide JSON, CSV, or STL data.") from csv_error

    # Fall back to attempting a binary STL parse.
    try:
        return list(_load_stl_points_binary(binary_data))
    except CADParseError as stl_error:
        raise CADParseError("Unsupported CAD file format. Provide JSON, CSV, or STL data.") from stl_error


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


def _generate_ascii_stl(
    points: List[PointData],
    positions: Iterable[Tuple[float, float, float]] | None = None,
    *,
    solid_name: str,
) -> str | None:
    """Create a minimal ASCII STL representation from triangle point data.

    The helper expects triples of vertices describing each triangle. If the
    points cannot form complete triangles (i.e. the total vertex count is not
    divisible by three) the function returns ``None`` and the caller can
    gracefully skip STL generation.
    """

    vertex_positions: List[Tuple[float, float, float]]
    if positions is None:
        vertex_positions = [point.position for point in points]
    else:
        vertex_positions = list(positions)
        if len(vertex_positions) != len(points):
            return None

    if len(points) % 3 != 0:
        return None

    def format_float(value: float) -> str:
        # ``:.6f`` keeps the STL readable while providing sufficient precision
        return f"{value:.6f}"

    lines: List[str] = [f"solid {solid_name}"]
    for index in range(0, len(points), 3):
        normal = points[index].normal
        vertices = vertex_positions[index : index + 3]
        lines.append(
            "  facet normal "
            + " ".join(format_float(component) for component in normal)
        )
        lines.append("    outer loop")
        for vertex in vertices:
            lines.append(
                "      vertex "
                + " ".join(format_float(component) for component in vertex)
            )
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append(f"endsolid {solid_name}")
    return "\n".join(lines)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def offset_view(request: HttpRequest) -> JsonResponse:
    """Handle CAD file uploads and return offset coordinates."""

    if request.method == "GET":
        return render(request, "cad/offset_form.html")

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

    response_payload: dict[str, object] = {
        "offset_points": offset_positions,
        "source_points": [list(point.position) for point in points],
    }

    source_stl = _generate_ascii_stl(points, solid_name="source_mesh")
    if source_stl is not None:
        response_payload["source_stl"] = source_stl

        offset_stl = _generate_ascii_stl(
            points, offset_positions, solid_name="offset_mesh"
        )
        if offset_stl is not None:
            response_payload["offset_stl"] = offset_stl

    return JsonResponse(response_payload)
