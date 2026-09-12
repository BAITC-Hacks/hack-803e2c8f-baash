import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "adapters" / "sdk" / "src"))
sys.path.insert(0, str(ROOT / "adapters" / "replay" / "src"))
