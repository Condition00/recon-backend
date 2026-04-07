from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent / "backend"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.tests.conftest import *  # noqa: F401,F403
