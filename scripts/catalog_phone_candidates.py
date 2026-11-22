#!/usr/bin/env python3
"""Catalog phone-use CANDIDATES from SRC009 for human visual verification.

The source YOLO class 1 ("Object" = mobile phone) is used ONLY to select
candidates; it is NEVER copied into the reference label. Every candidate is
verified by a human on the generated review sheets before phone_detection is
set to YES. Protocol §7 is therefore respected.

    python scripts/catalog_phone_candidates.py --root . --stride 10
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
from pathlib import Path

CATALOG_HEADER = [
    "frame_id", "dataset_id", "source_video", "source_rel_path",
    "timestamp_ms", "frame_file", "width", "height", "frame_sha256",
    "extraction_date", "tool",
]
PHONE_CLASS = "1"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Catalog phone candidates")
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--stride", type=int, default=10)
    args = ap.parse_args(argv)
    root = args.root.resolve()
    base = root / "data" / "raw" / "DrowsinessEdge" / "Drowsiness Dataset"
    catalog_path = root / "data" / "catalog" / "frame_samples.csv"
    out_dir = root / "data" / "_incoming" / "frame_catalog" / "DrowsinessEdge_phone"
    out_dir.mkdir(parents=True, exist_ok=True)

    candidates = []
    for label in sorted(base.rglob("labels/*.txt")):
        lines = [ln.split() for ln in label.read_text(errors="ignore").splitlines() if ln.strip()]
        if not any(parts[0] == PHONE_CLASS for parts in lines):
            continue
        image = label.parent.parent / "images" / (label.stem + ".jpg")
        if image.exists():
            candidates.append(image)
    candidates.sort()
    selected = candidates[:: args.stride]
    print(f"{len(candidates)} candidate images; selecting {len(selected)} (stride {args.stride})")

    with catalog_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    known = {(r["source_rel_path"], r["timestamp_ms"]) for r in rows}
    counter = max((int(r["frame_id"][2:]) for r in rows if r["frame_id"].startswith("FR")), default=0)
    import cv2

    added = 0
    for image in selected:
        rel = image.relative_to(root).as_posix()
        if (rel, "1") in known:
            continue
        img = cv2.imread(str(image))
        if img is None:
            continue
        dest = out_dir / image.name
        shutil.copyfile(image, dest)
        counter += 1
        rows.append({
            "frame_id": f"FR{counter:06d}",
            "dataset_id": "SRC009",
            "source_video": image.name,
            "source_rel_path": rel,
            "timestamp_ms": "1",
            "frame_file": dest.relative_to(root).as_posix(),
            "width": str(img.shape[1]),
            "height": str(img.shape[0]),
            "frame_sha256": _sha256(dest),
            "extraction_date": "2026-11-21",
            "tool": "phone_candidate_class1 (visual verification required)",
        })
        known.add((rel, "1"))
        added += 1

    with catalog_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CATALOG_HEADER)
        w.writeheader()
        w.writerows(rows)

    review_dir = root / "data" / "_incoming" / "phone_review_sheets"
    review_dir.mkdir(parents=True, exist_ok=True)
    import numpy as np

    new_rows = [r for r in rows if r["tool"].startswith("phone_candidate")]
    cols, rcount, tw, th = 4, 3, 360, 240
    for sidx in range(0, len(new_rows), cols * rcount):
        batch = new_rows[sidx:sidx + cols * rcount]
        canvas = np.zeros((rcount * th, cols * tw, 3), dtype="uint8")
        for i, row in enumerate(batch):
            frame = cv2.imread(row["frame_file"])
            if frame is None:
                continue
            frame = cv2.resize(frame, (tw, th))
            idx = sidx + i
            cv2.rectangle(frame, (0, 0), (tw, 22), (0, 0, 0), -1)
            cv2.putText(frame, f"P#{idx} {Path(row['frame_file']).stem[:28]}",
                        (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                        (0, 255, 255), 1, cv2.LINE_AA)
            r, c = divmod(i, cols)
            canvas[r*th:(r+1)*th, c*tw:(c+1)*tw] = frame
        cv2.imwrite(str(review_dir / f"phone_sheet_{sidx//(cols*rcount):03d}.jpg"),
                    canvas, [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(f"added {added} candidates; catalog has {len(rows)} frames")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
