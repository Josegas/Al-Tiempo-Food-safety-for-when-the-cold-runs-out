"""Build deployment artifacts (no Docker needed).

    python scripts/package_agent.py   -> build/agent.zip      (AgentCore Runtime, ARM64, Python 3.12)
                                      -> build/boto3_layer/   (Lambda layer: recent boto3 for the API)

- Dependencies are installed as linux/aarch64 wheels (works from an x86 laptop or CI, no Docker).
- The zip is deterministic (sorted entries, fixed timestamps): same code -> same hash -> CDK
  does not upload or update the runtime when nothing changed.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
DEPS = BUILD / "deps"
ZIP = BUILD / "agent.zip"
CODE = ["main.py", "agent", "rules", "fixtures"]
SKIP_PARTS = {"__pycache__", "tests", ".pytest_cache"}
FIXED_DATE = (2026, 1, 1, 0, 0, 0)


def install_deps() -> None:
    req = (ROOT / "requirements.txt").read_bytes()
    stamp = DEPS / ".requirements.sha256"
    digest = hashlib.sha256(req).hexdigest()
    if stamp.exists() and stamp.read_text() == digest:
        return  # cached
    shutil.rmtree(DEPS, ignore_errors=True)
    DEPS.mkdir(parents=True)
    subprocess.run(  # noqa: S603
        [
            sys.executable, "-m", "pip", "install", "--quiet", "--no-compile",
            "--target", str(DEPS),
            "--platform", "manylinux2014_aarch64", "--platform", "manylinux_2_28_aarch64",
            "--python-version", "3.12", "--implementation", "cp", "--only-binary=:all:",
            "-r", str(ROOT / "requirements.txt"),
        ],
        check=True,
    )  # fmt: skip
    stamp.write_text(digest)


BOTO3_LAYER = BUILD / "boto3_layer"
BOTO3_VERSION = "1.43.123"  # same as the agent; includes the bedrock-agentcore client


def build_boto3_layer() -> None:
    stamp = BOTO3_LAYER / ".version"
    if stamp.exists() and stamp.read_text() == BOTO3_VERSION:
        return
    shutil.rmtree(BOTO3_LAYER, ignore_errors=True)
    (BOTO3_LAYER / "python").mkdir(parents=True)
    subprocess.run(  # noqa: S603
        [
            sys.executable, "-m", "pip", "install", "--quiet", "--no-compile",
            "--target", str(BOTO3_LAYER / "python"), f"boto3=={BOTO3_VERSION}",
        ],
        check=True,
    )  # fmt: skip
    stamp.write_text(BOTO3_VERSION)


def files_to_zip() -> list[tuple[Path, str]]:
    entries: list[tuple[Path, str]] = []
    for path in sorted(DEPS.rglob("*")):
        rel = path.relative_to(DEPS)
        if path.is_file() and not SKIP_PARTS & set(rel.parts) and path.suffix != ".pyc":
            if rel.name != ".requirements.sha256":
                entries.append((path, rel.as_posix()))
    for item in CODE:
        src = ROOT / item
        paths = [src] if src.is_file() else sorted(src.rglob("*"))
        for path in paths:
            rel = path.relative_to(ROOT)
            if path.is_file() and not SKIP_PARTS & set(rel.parts) and path.suffix != ".pyc":
                entries.append((path, rel.as_posix()))
    return sorted(entries, key=lambda e: e[1])


def build_zip() -> None:
    tmp = ZIP.with_suffix(".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path, arcname in files_to_zip():
            info = zipfile.ZipInfo(arcname, date_time=FIXED_DATE)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, path.read_bytes())
    tmp.replace(ZIP)


if __name__ == "__main__":
    install_deps()
    build_zip()
    build_boto3_layer()
    size_mb = ZIP.stat().st_size / 1_000_000
    digest = hashlib.sha256(ZIP.read_bytes()).hexdigest()[:12]
    print(f"{ZIP.relative_to(ROOT)}  {size_mb:.1f} MB  sha256:{digest}")
