from pathlib import Path

import pytest

from app.renderer_adapter import RendererAdapterError, build_command


def test_chromium_adapter_preserves_input_output_contract(tmp_path):
    source = tmp_path / "input.html"
    target = tmp_path / "output.pdf"
    assert build_command("chromium", ["node", "print.mjs"], source, target) == [
        "node", "print.mjs", str(source), str(target)]


def test_prince_adapter_adds_isolation_and_prince_output_flags(tmp_path):
    source = tmp_path / "input.html"
    target = tmp_path / "output.pdf"
    license_file = Path("/licenses/prince.dat")
    command = build_command("prince", ["prince"], source, target, license_file)
    assert command == ["prince", "--no-local-files", "--no-network",
                       f"--license-file={license_file}", str(source), "-o", str(target)]


def test_renderer_adapter_rejects_unknown_renderer(tmp_path):
    with pytest.raises(RendererAdapterError, match="unsupported PDF renderer"):
        build_command("unknown", ["engine"], tmp_path / "in.html", tmp_path / "out.pdf")
