#!/usr/bin/env python3
"""Zip generated datasets plus the generation code and prompt: python generation/build_zip.py <part>"""
import os, sys, zipfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
part = sys.argv[1] if len(sys.argv) > 1 else "all"
out = os.path.join("/mnt/user-data/outputs", f"veriq_datasets_{part}.zip")
os.makedirs(os.path.dirname(out), exist_ok=True)
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for sub in ("data", "generation"):
        for d, _, files in os.walk(os.path.join(ROOT, sub)):
            if "__pycache__" in d: continue
            for f in files:
                p = os.path.join(d, f); z.write(p, os.path.relpath(p, ROOT))
print(out)
