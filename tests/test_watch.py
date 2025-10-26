#!/usr/bin/env python3
import subprocess
import shutil
import time
from pathlib import Path
import os
import yaml
import pytest

from PIL import Image

BASE = Path(__file__).parent
INPUT = BASE / "test-images"
TMP = BASE / "tmp" / "watch"
TMP.mkdir(parents=True, exist_ok=True)

_created_tmp_files = set()


# --- Helpers ---

def run_watcher(input_file, args=None, subdir=None, timeout=5):
    """
    Run optimize-images in watch mode, copy input_file into TMP (or subdir),
    and wait until it's processed or timeout expires.
    """
    target_dir = TMP
    if subdir:
        target_dir = TMP / subdir
        target_dir.mkdir(parents=True, exist_ok=True)

    tmp_file = target_dir / input_file.name
    if tmp_file.exists():
        tmp_file.unlink()
    shutil.copy(input_file, tmp_file)
    _created_tmp_files.add(tmp_file)

    cmd = ["optimize-images", "-wd", str(TMP)] + (args or []) + ["--quiet"]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait until file size changes or timeout
    size_before = os.path.getsize(tmp_file)
    out_file = tmp_file
    deadline = time.time() + timeout
    while time.time() < deadline:
        if out_file.exists() and os.path.getsize(out_file) != size_before:
            break
        time.sleep(0.5)

    # Stop watcher
    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()

    return out_file


def has_exif(path):
    try:
        with Image.open(path) as img:
            exif = getattr(img, "getexif", None)
            if exif is None:
                return False
            data = exif() if callable(exif) else exif
            return bool(data and len(data) > 0)
    except Exception:
        return False


def file_size(path):
    return os.path.getsize(path)


def image_info(path):
    with Image.open(path) as img:
        fmt = img.format
        if fmt == "JPG":
            fmt = "JPEG"
        return fmt, img.size, img.info


def load_tests():
    with open(BASE / "test_watch_config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["tests"]


def case_id(t):
    base = t.get("name") or t.get("input", "unnamed")
    note = t.get("note")
    return f"{base} [{note}]" if note else base


# --- Parametrized tests ---

@pytest.mark.parametrize("case", load_tests(), ids=case_id)
def test_watch_case(case):
    input_file = INPUT / case["input"]
    assert input_file.exists(), f"MISSING input: {case['input']}"

    args = case.get("args") or []
    subdir = case.get("subdir")
    out_file = run_watcher(input_file, args=args, subdir=subdir)

    context = {
        "orig": input_file,
        "out": out_file,
        "file_size": file_size,
        "image_info": image_info,
        "has_exif": has_exif,
    }

    try:
        ok = eval(case["check"], context)
    except Exception as e:
        pytest.fail(f"Exception in check: {e}")
    else:
        assert ok, "Check failed"
    finally:
        # Remove only files we created, leave any pre-existing files intact
        for temp_file in list(_created_tmp_files):
            try:
                if temp_file.exists():
                    temp_file.unlink()
            finally:
                _created_tmp_files.discard(temp_file)


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main(["-v", "--color=yes", __file__]))
