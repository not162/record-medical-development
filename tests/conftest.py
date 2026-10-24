import sys
from pathlib import Path

# Add services/ai-api to sys.path so app modules are directly importable in all tests
api_root = Path(__file__).resolve().parent.parent / "services" / "ai-api"
if str(api_root) not in sys.path:
    sys.path.insert(0, str(api_root))
