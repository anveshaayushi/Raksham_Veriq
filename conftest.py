import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


import os as _os

import pytest as _pytest


@_pytest.fixture(autouse=True)
def _restore_veriq_env():
    """The app's config.apply() sets VERIQ_* environment variables for the running process (e.g. inside AppTest).
    Restore them after every test so one test can never change another's environment."""
    before = {k: v for k, v in _os.environ.items() if k.startswith("VERIQ_")}
    yield
    for k in [k for k in _os.environ if k.startswith("VERIQ_") and k not in before]:
        del _os.environ[k]
    _os.environ.update(before)
