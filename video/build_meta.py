"""Write src/data/scenes.json: per scene the narration audio, its duration and caption sentences.

  python3 build_meta.py      (after regenerating narration with Kokoro)
"""

import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
scenes = []
for txt in sorted((HERE / "narration").glob("scene*.txt"), key=lambda p: int(p.stem[5:])):
    wav = HERE / "public" / "audio" / f"{txt.stem}.wav"
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(wav)],
                               capture_output=True, text=True, check=True).stdout)
    sentences = [s.strip() for s in re.split(r"(?<=[.?!:])\s+", txt.read_text().strip()) if s.strip()]
    scenes.append({"id": txt.stem, "audio": f"audio/{wav.name}", "seconds": round(dur, 2), "captions": sentences})
(HERE / "src" / "data" / "scenes.json").write_text(json.dumps(scenes, indent=1))
print(sum(s["seconds"] for s in scenes), "s of narration in", len(scenes), "scenes")
