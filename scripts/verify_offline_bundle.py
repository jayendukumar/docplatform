"""Verify the local inputs required by the documented offline bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _verify_assets(manifest: dict, manifest_path: Path) -> list[str]:
    assets = manifest.get("assets", [])
    if not isinstance(assets, list):
        return ["assets must be a list"]
    errors: list[str] = []
    root = manifest_path.parent.resolve()
    for index, asset in enumerate(assets):
        prefix = f"assets[{index}]"
        if not isinstance(asset, dict):
            errors.append(f"{prefix} must be an object")
            continue
        relative = asset.get("path")
        digest = asset.get("sha256")
        if not isinstance(relative, str) or not relative.strip():
            errors.append(f"{prefix}.path must be a non-empty relative path")
            continue
        candidate = (root / relative).resolve()
        if candidate != root and root not in candidate.parents:
            errors.append(f"{prefix}.path escapes the manifest directory")
            continue
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
            errors.append(f"{prefix}.sha256 must be a 64-character hexadecimal digest")
            continue
        if not candidate.is_file():
            errors.append(f"{prefix}.path does not identify a file: {relative}")
            continue
        actual = hashlib.sha256(candidate.read_bytes()).hexdigest()
        if actual.casefold() != digest.casefold():
            errors.append(f"{prefix}.sha256 does not match: {relative}")
    return errors


def verify_manifest(manifest_path: Path, *, inspect_images: bool = True) -> list[str]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if manifest.get("format") != "docplatform-offline-bundle-v1":
        errors.append("unsupported offline bundle format")
    if manifest.get("network_required_at_runtime") is not False:
        errors.append("runtime network policy must be false")
    if not isinstance(manifest.get("required_images"), list) or not manifest["required_images"]:
        errors.append("required_images must be a non-empty list")
    if not isinstance(manifest.get("fonts_and_models"), str) or not manifest["fonts_and_models"].strip():
        errors.append("fonts_and_models must explicitly describe bundled or unbundled assets")
    if not isinstance(manifest.get("verification"), list) or not manifest["verification"]:
        errors.append("verification must be a non-empty list")
    errors.extend(_verify_assets(manifest, manifest_path))
    if inspect_images:
        for image in manifest.get("required_images", []):
            result = subprocess.run(["docker", "image", "inspect", str(image)],
                                    capture_output=True, text=True)
            if result.returncode != 0:
                errors.append(f"required image is not available locally: {image}")
    return errors


def verify_compose(compose_file: Path) -> str | None:
    result = subprocess.run(["docker", "compose", "-f", str(compose_file), "config", "--quiet"],
                            capture_output=True, text=True)
    if result.returncode:
        return result.stderr.strip() or "docker compose config failed"
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "templates" / "docplatform-offline-bundle.json")
    parser.add_argument("--compose", type=Path, default=ROOT / "compose.yaml")
    parser.add_argument("--skip-image-inspect", action="store_true")
    args = parser.parse_args()
    errors = verify_manifest(args.manifest, inspect_images=not args.skip_image_inspect)
    compose_error = verify_compose(args.compose)
    if compose_error:
        errors.append(compose_error)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("offline bundle inputs verified; network-isolated installation still requires an operator run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
