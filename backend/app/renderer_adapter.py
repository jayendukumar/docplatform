"""Renderer-specific command construction behind the PDF adapter boundary."""
from __future__ import annotations

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[2]


class RendererAdapterError(ValueError):
    pass


def default_command(renderer: str) -> list[str]:
    """Return the packaged command for the default renderer when available."""
    if renderer != "chromium":
        return []
    node = shutil.which("node")
    script = ROOT / "scripts" / "render_chromium_candidate.mjs"
    if node and script.is_file():
        return [node, str(script)]
    return []


def build_command(renderer: str, command: list[str], source: Path, target: Path,
                  license_file: Path | None = None) -> list[str]:
    """Build a bounded local command without allowing template input to add flags."""
    if renderer not in {"chromium", "prince"}:
        raise RendererAdapterError(f"unsupported PDF renderer: {renderer}")
    if not command or not all(isinstance(part, str) and part for part in command):
        raise RendererAdapterError("PDF renderer command is not configured")
    if renderer == "chromium":
        return [*command, str(source), str(target)]
    result = [*command, "--no-local-files", "--no-network"]
    if license_file is not None:
        result.extend([f"--license-file={license_file}"])
    result.extend([str(source), "-o", str(target)])
    return result
