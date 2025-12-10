import sys
from pathlib import Path

# Add src to path
src_path = Path("/home/kira/git/devopsnextgenx/caption-extractor/src")
sys.path.insert(0, str(src_path))

try:
    from caption_extractor.api_service import app
    print("Import successful")
except Exception as e:
    print(f"Import failed: {e}")
    sys.exit(1)
