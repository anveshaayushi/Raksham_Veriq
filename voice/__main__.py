"""Run one clip from the command line:  python -m voice path\\to\\clip.opus"""
import json
import sys
from pathlib import Path

from voice.service import analyse

if len(sys.argv) != 2:
    print("usage: python -m voice <audio file>")
    raise SystemExit(2)
p = Path(sys.argv[1])
try:
    data = p.read_bytes()
except OSError as e:
    print(f"cannot read {p}: {e}")
    raise SystemExit(1)
print(json.dumps(analyse(p.name, data, p.name).to_dict(), indent=2))
