import os
from pathlib import Path
import sys

os.environ.setdefault("MODE", "testing")
os.environ.setdefault("APP_BASE_URL", "http://localhost:5173")
os.environ.setdefault("API_BASE_URL", "http://localhost:8000")
os.environ.setdefault("FRONTEND_REDIRECT_AFTER_LOGIN", "http://localhost:5173/auth/callback")

ROOT_DIR = Path(__file__).resolve().parent / "backend"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.tests.conftest import *  # noqa: F401,F403
