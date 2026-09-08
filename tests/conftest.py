import sys
from pathlib import Path

# lib/ をテストから import できるようにする（パッケージングはしない方針）
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
