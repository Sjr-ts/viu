#!/usr/bin/env python3
"""NightEyes — deterministic sample download of an MIT-licensed face-crop source.

Protocol §7: the source's EAR/MAR/heuristic labels are NEVER read or used as
reference labels. Only the pixels (filenames) are acquired; every reference
label is assigned later by human visual annotation of the review sheets.

    python scripts/acquire_hf_facecrops.py --root . --stride 10
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.request
from pathlib import Path

DATASET_ID = "notgoodkeeper/cnn-based-drowsiness-detection-data"
API = f"https://huggingface.co/api/datasets/{DATASET_ID}"
RESOLVE = f"https://huggingface.co/datasets/{DATASET_ID}/resolve/main/"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Download deterministic image sample")
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--stride", type=int, default=10)
    args = ap.parse_args(argv)
    if args.stride < 1:
        raise SystemExit("ERROR: --stride must be >= 1")
    root = args.root.resolve()
    dest_dir = root / "data" / "raw" / "AutoLabeledFaceCrops" / "images"
    dest_dir.mkdir(parents=True, exist_ok=True)

    with urllib.request.urlopen(API, timeout=60) as fh:
        meta = json.load(fh)
    names = sorted(x["rfilename"] for x in meta.get("siblings", [])
                   if x["rfilename"].startswith("images/")
                   and x["rfilename"].lower().endswith((".png", ".jpg")))
    selected = names[:: args.stride]
    print(f"source lists {len(names)} images; downloading {len(selected)} (stride {args.stride})")

    records = []
    for i, name in enumerate(selected, start=1):
        dest = dest_dir / Path(name).name
        url = RESOLVE + name + "?download=true"
        if not dest.exists():
            for attempt in range(1, 5):
                try:
                    urllib.request.urlretrieve(url, dest)
                    break
                except Exception as exc:
                    if attempt == 4:
                        raise SystemExit(f"failed {url}: {exc}")
                    time.sleep(2 * attempt)
        records.append({
            "source_url": url,
            "local_path": dest.relative_to(root).as_posix(),
            "sha256": _sha256(dest),
            "bytes": dest.stat().st_size,
        })
        if i % 25 == 0:
            print(f"  {i}/{len(selected)}")

    manifest = root / "data" / "catalog" / "hf_facecrops_manifest.json"
    manifest.write_text(json.dumps({
        "dataset_id": "SRC010",
        "source_dataset": DATASET_ID,
        "license": "MIT (Hugging Face dataset card)",
        "protocol_7_note": "heuristic EAR/MAR/drowsiness labels excluded; human re-annotation required",
        "selection": f"deterministic every {args.stride}th image of sorted filename list",
        "files": records,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"manifest: {manifest.relative_to(root).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
