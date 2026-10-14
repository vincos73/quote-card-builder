"""Portable, self-contained brand kits for Quote Card Builder.

Validation is pure; call :func:`brand_from_kit` explicitly to materialize
embedded assets into a local asset directory.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

SCHEMA = "qcb-brand-kit"
SCHEMA_VERSION = 1
MAX_KIT_BYTES = 8 * 1024 * 1024
MAX_ASSET_BYTES = 4 * 1024 * 1024
MAX_TOTAL_ASSET_BYTES = 8 * 1024 * 1024
COLOR_KEYS = ("primary", "accent", "background", "text")
FONT_VARIANTS = ("regular", "bold", "italic", "bold_italic")
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
FONT_MIMES = {"font/ttf": ".ttf", "font/otf": ".otf", "font/woff": ".woff", "font/woff2": ".woff2",
              "application/x-font-ttf": ".ttf", "application/vnd.ms-opentype": ".otf"}
LOGO_MIMES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/svg+xml": ".svg"}
MAX_SVG_BYTES = 2 * 1024 * 1024
SVG_NS = "http://www.w3.org/2000/svg"
SVG_ELEMENTS = {"svg", "title", "desc", "g", "path", "rect", "circle", "ellipse", "line", "polyline", "polygon"}
SVG_ATTRIBUTES = {"xmlns", "viewBox", "role", "aria-label", "aria-labelledby", "fill", "fill-rule",
                  "fill-opacity", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin",
                  "stroke-miterlimit", "stroke-opacity", "opacity", "transform", "d", "x", "y",
                  "x1", "y1", "x2", "y2", "cx", "cy", "r", "rx", "ry", "width", "height",
                  "points", "id"}


def _validate_svg(data: bytes) -> None:
    if len(data) > MAX_SVG_BYTES:
        _fail(f"SVG logo exceeds the {MAX_SVG_BYTES}-byte SVG limit")
    try:
        source = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("SVG logo must be UTF-8") from exc
    # ElementTree expands internal entities. Reject declarations before parse.
    if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", source, re.IGNORECASE):
        _fail("SVG declarations and entities are not allowed")
    if re.search(r"<\?xml-stylesheet\b", source, re.IGNORECASE):
        _fail("SVG external stylesheets are not allowed")
    try:
        root = ET.fromstring(source)
    except ET.ParseError as exc:
        raise ValueError("SVG logo is not well-formed XML") from exc
    if root.tag != f"{{{SVG_NS}}}svg":
        _fail("SVG logo must have an SVG namespace root")
    for element in root.iter():
        if not isinstance(element.tag, str) or not element.tag.startswith(f"{{{SVG_NS}}}"):
            _fail("SVG logo contains a non-SVG or foreign element")
        name = element.tag.rsplit("}", 1)[-1]
        if name not in SVG_ELEMENTS:
            _fail(f"SVG logo element {name!r} is not allowed")
        for key, value in element.attrib.items():
            attr = key.rsplit("}", 1)[-1]
            if attr.lower().startswith("on") or attr not in SVG_ATTRIBUTES:
                _fail(f"SVG logo attribute {attr!r} is not allowed")
            if re.search(r"url\s*\(|(?:https?:|file:|data:|javascript:|//)", value, re.IGNORECASE):
                _fail("SVG logo external or resource references are not allowed")
            if attr in {"href", "xlink:href", "style"}:
                _fail(f"SVG logo attribute {attr!r} is not allowed")


def _fail(message: str) -> None:
    raise ValueError(message)


def _asset_bytes(asset: Any, allowed: dict[str, str], label: str) -> tuple[str, bytes]:
    if not isinstance(asset, dict) or set(asset) != {"mime_type", "data_base64"}:
        _fail(f"{label} must contain mime_type and data_base64 only")
    mime = asset["mime_type"]
    encoded = asset["data_base64"]
    if not isinstance(mime, str) or mime not in allowed:
        _fail(f"{label} has unsupported MIME type (SVG logos are not supported)")
    if not isinstance(encoded, str) or len(encoded) > ((MAX_ASSET_BYTES + 2) // 3) * 4:
        _fail(f"{label} exceeds the {MAX_ASSET_BYTES}-byte asset limit")
    try:
        data = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        _fail(f"{label}.data_base64 is invalid base64")
    if not data or len(data) > MAX_ASSET_BYTES:
        _fail(f"{label} must be between 1 and {MAX_ASSET_BYTES} bytes")
    if mime in LOGO_MIMES:
        if mime == "image/svg+xml":
            _validate_svg(data)
            valid = True
        else:
            valid = ((mime == "image/png" and data.startswith(b"\x89PNG\r\n\x1a\n")) or
                 (mime == "image/jpeg" and data.startswith(b"\xff\xd8\xff")) or
                 (mime == "image/webp" and len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"))
        if not valid:
            _fail("logo bytes do not match their declared image MIME type")
        if mime != "image/svg+xml":
            try:
                from PIL import Image
                import io
                with Image.open(io.BytesIO(data)) as image:
                    image.verify()
            except ImportError as exc:
                raise ValueError("Pillow is required to validate raster logo files") from exc
            except Exception as exc:
                raise ValueError("logo image is truncated or invalid") from exc
    else:
        signatures = {"font/ttf": data[:4] == b"\x00\x01\x00\x00" or data[:4] == b"true",
                      "application/x-font-ttf": data[:4] == b"\x00\x01\x00\x00" or data[:4] == b"true",
                      "font/otf": data[:4] == b"OTTO", "application/vnd.ms-opentype": data[:4] == b"OTTO",
                      "font/woff": data[:4] == b"wOFF", "font/woff2": data[:4] == b"wOF2"}
        if not signatures.get(mime, False):
            _fail("font bytes do not match their declared MIME type")
        try:
            from fontTools.ttLib import TTFont
            import io
            font = TTFont(io.BytesIO(data), lazy=False)
            font.close()
        except ImportError as exc:
            raise ValueError("fontTools is required to validate font files") from exc
        except Exception as exc:
            raise ValueError("font could not be parsed by fontTools") from exc
    return mime, data


def normalize_brand_kit(value: Any) -> dict[str, Any]:
    """Validate and canonicalize a portable qcb-brand-kit object."""
    try:
        wire = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ValueError("brand kit must be JSON serializable") from exc
    if len(wire) > MAX_KIT_BYTES:
        _fail(f"brand kit exceeds the {MAX_KIT_BYTES}-byte limit")
    if not isinstance(value, dict) or set(value) - {"schema", "schema_version", "name", "colors", "font", "logo", "logo_variants"}:
        _fail("brand kit contains unsupported fields")
    if value.get("schema") != SCHEMA or value.get("schema_version") != SCHEMA_VERSION:
        _fail("brand kit schema or schema_version is unsupported")
    name = value.get("name")
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 80:
        _fail("brand kit name must contain 1 to 80 characters")
    colors = value.get("colors")
    if not isinstance(colors, dict) or set(colors) != set(COLOR_KEYS):
        _fail("brand kit colors must contain primary, accent, background, and text")
    normalized_colors = {}
    for key in COLOR_KEYS:
        color = colors.get(key)
        if not isinstance(color, str) or not HEX.fullmatch(color):
            _fail(f"colors.{key} must be an exact #RRGGBB color")
        normalized_colors[key] = color.upper()
    result: dict[str, Any] = {"schema": SCHEMA, "schema_version": SCHEMA_VERSION,
                              "name": name.strip(), "colors": normalized_colors}
    total = 0
    font = value.get("font")
    if font is not None:
        if not isinstance(font, dict) or set(font) - {"family", *FONT_VARIANTS}:
            _fail("font contains unsupported fields")
        family = font.get("family")
        if not isinstance(family, str) or not family.strip() or len(family.strip()) > 120:
            _fail("font.family must be a nonempty family name")
        normalized_font: dict[str, Any] = {"family": family.strip()}
        for variant in FONT_VARIANTS:
            if variant in font:
                mime, data = _asset_bytes(font[variant], FONT_MIMES, f"font.{variant}")
                total += len(data)
                normalized_font[variant] = {"mime_type": mime, "data_base64": base64.b64encode(data).decode("ascii")}
        result["font"] = normalized_font
    logo = value.get("logo")
    if logo is not None:
        mime, data = _asset_bytes(logo, LOGO_MIMES, "logo")
        total += len(data)
        result["logo"] = {"mime_type": mime, "data_base64": base64.b64encode(data).decode("ascii")}
    variants = value.get("logo_variants")
    if variants is not None:
        if not isinstance(variants, dict) or not variants or set(variants) - {"dark", "light"}:
            _fail("logo_variants must contain dark and/or light assets only")
        normalized_variants = {}
        for key, asset in variants.items():
            mime, data = _asset_bytes(asset, LOGO_MIMES, f"logo_variants.{key}")
            total += len(data)
            normalized_variants[key] = {"mime_type": mime, "data_base64": base64.b64encode(data).decode("ascii")}
        result["logo_variants"] = normalized_variants
    if total > MAX_TOTAL_ASSET_BYTES:
        _fail(f"decoded brand assets exceed the {MAX_TOTAL_ASSET_BYTES}-byte total limit")
    return result


def kit_from_brand(brand: Any, base_dir: str | os.PathLike[str]) -> dict[str, Any]:
    """Embed valid local font/logo assets referenced by a renderer brand."""
    if not isinstance(brand, dict):
        _fail("brand must be an object")
    colors = brand.get("colors")
    # Keep palette validation aligned with the public kit schema.
    kit: dict[str, Any] = {"schema": SCHEMA, "schema_version": SCHEMA_VERSION,
                           "name": brand.get("name"), "colors": colors}
    base = Path(base_dir).resolve()

    def embed(section: dict[str, Any], path_key: str, allowed: dict[str, str], label: str) -> dict[str, str] | None:
        value = section.get(path_key)
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            _fail(f"{label} path must be a nonempty string")
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = base / candidate
        candidate = candidate.resolve(strict=True)
        try:
            candidate.relative_to(base)
        except ValueError:
            _fail(f"{label} path must resolve inside base_dir")
        if not candidate.is_file() or candidate.stat().st_size > MAX_ASSET_BYTES:
            _fail(f"{label} file is missing or exceeds the asset limit")
        ext = candidate.suffix.lower()
        mime = next((m for m, suffix in allowed.items() if suffix == ext), None)
        if mime is None:
            _fail(f"{label} file extension is unsupported")
        data = candidate.read_bytes()
        obj = {"mime_type": mime, "data_base64": base64.b64encode(data).decode("ascii")}
        _asset_bytes(obj, allowed, label)
        return obj

    font = brand.get("font")
    if font is not None:
        if not isinstance(font, dict):
            _fail("brand.font must be an object")
        portable_font: dict[str, Any] = {"family": font.get("family")}
        for variant in FONT_VARIANTS:
            path = embed(font, variant + "_path", FONT_MIMES, "font." + variant)
            if path is not None:
                portable_font[variant] = path
        kit["font"] = portable_font
    logo = brand.get("logo")
    if logo is not None:
        if not isinstance(logo, dict):
            _fail("brand.logo must be an object")
        dark_path, light_path = logo.get("dark_path"), logo.get("light_path")
        dark = embed({"file_path": dark_path}, "file_path", LOGO_MIMES, "logo") if dark_path else None
        light = embed({"file_path": light_path}, "file_path", LOGO_MIMES, "logo") if light_path else None
        primary = dark or light
        if primary is not None:
            kit["logo"] = primary
        if dark is not None and light is not None and dark["data_base64"] != light["data_base64"]:
            kit["logo_variants"] = {"dark": dark, "light": light}
    return normalize_brand_kit(kit)


def brand_from_kit(kit: Any, asset_dir: str | os.PathLike[str]) -> dict[str, Any]:
    """Validate and atomically materialize assets, returning renderer brand data."""
    normalized = normalize_brand_kit(kit)
    target = Path(asset_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)
    brand: dict[str, Any] = {"name": normalized["name"], "colors": normalized["colors"]}

    def write(asset: dict[str, str]) -> str:
        mime, data = _asset_bytes(asset, {**FONT_MIMES, **LOGO_MIMES}, "asset")
        suffix = (FONT_MIMES | LOGO_MIMES)[mime]
        path = target / (hashlib.sha256(data).hexdigest() + suffix)
        if not path.exists():
            fd, tmp_name = tempfile.mkstemp(prefix=".qcb-", dir=target)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(tmp_name, path)
            finally:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)
        return str(path)

    font = normalized.get("font")
    if font is not None:
        renderer_font: dict[str, Any] = {"family": font["family"]}
        for variant, key in (("regular", "regular_path"), ("bold", "bold_path"),
                             ("italic", "italic_path"), ("bold_italic", "bold_italic_path")):
            if variant in font:
                renderer_font[key] = write(font[variant])
        brand["font"] = renderer_font
    if "logo" in normalized:
        logo_path = write(normalized["logo"])
        brand["logo"] = {"dark_path": logo_path, "light_path": logo_path}
    if "logo_variants" in normalized:
        brand.setdefault("logo", {})
        for variant, asset in normalized["logo_variants"].items():
            brand["logo"][variant + "_path"] = write(asset)
    return brand
