# vision_extract_tool/try_image.py — chạy thử trên 1 ảnh, chưa cần endpoint upload hay DB
import json
import sys
from . import run_engine

if __name__ == "__main__":
    print(json.dumps(run_engine(sys.argv[1]), ensure_ascii=False, indent=2))