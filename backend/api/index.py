import sys
import os

# Ensure the backend directory is on the Python path so imports resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app  # noqa: E402, F401
