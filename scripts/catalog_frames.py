#!/usr/bin/env python3
"""NightEyes — sample frame catalog (traceable image inventory).

Scans videos under data/raw/ and extracts sample frames into
data/_incoming/frame_catalog/, registering every frame in
data/catalog/frame_samples.csv with SHA-256 for traceability.

    python scripts/catalog_frames.py --root . --positions 0.1,0.5,0.9

Notes:
    * Frames are DERIVED artifacts (quality_control/) — originals in
      data/raw/ are never modified.
    * Idempotent: a (source_video, timestamp_ms) already in the catalog
      is skipped; use --rebuild to regenerate everything.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
import sys
from datetime import date
from pathlib import Path

import cv2

VIDEO_EXTS = {".avi", ".mp4", ".mov", ".mkv", ".mjpeg", ".mpg", ".mpeg"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png"}

FRAME_HEADER = [
    "frame_id", "dataset_id", "source_video", "source_rel_path",
    "timestamp_ms", "frame_file", "width", "height", "frame_sha256",
    "extraction_date", "tool",
]

# data/raw/<dir> -> dataset_id (kept in sync with scripts/acquire.py)
DIR_TO_DATASET = {
    "DMD": "SRC001", "UTA_RLDD": "SRC002", "YawDD": "SRC003",
    "DROZY": "SRC004", "NTHU_DDD": "SRC005", "AUC_Distracted": "SRC006",
    "State_Farm": "SRC007", "UL_DD": "SRC008",
    "DrowsinessEdge": "SRC009",
    "AutoLabeledFaceCrops": "SRC010",
}


def _read_frames_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _write_frames_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FRAME_HEADER)
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _next_frame_id(rows: list[dict]) -> int:
    n = 0
    for r in rows:
        fid = (r.get("frame_id") or "").strip()
        if fid.startswith("FR") and fid[2:].isdigit():
            n = max(n, int(fid[2:]))
    return n


def catalog(root: Path, positions: list[float], rebuild: bool = False,
            image_stride: int = 10) -> list[dict]:
    raw = root / "data" / "raw"
    out_dir = root / "data" / "_incoming" / "frame_catalog"
    csv_path = root / "data" / "catalog" / "frame_samples.csv"
    rows = [] if rebuild else _read_frames_csv(csv_path)
    if rebuild:
        if out_dir.exists():
            for old in out_dir.rglob("*.jpg"):
                old.unlink()
    existing = {
        (r["source_rel_path"], r["timestamp_ms"]) for r in rows
    }
    counter = _next_frame_id(rows)

    videos = [
        p for p in sorted(raw.rglob("*"))
        if p.is_file() and p.suffix.lower() in VIDEO_EXTS
    ]
    if not videos:
        print("no videos found under data/raw/ (only static images will be cataloged)")

    for video in videos:
        rel = video.relative_to(root).as_posix()
        dataset_dir = video.relative_to(raw).parts[0]
        dataset_id = DIR_TO_DATASET.get(dataset_dir, "SRC000")
        cap = cv2.VideoCapture(str(video))
        if not cap.isOpened():
            print(f"WARNING: cannot open {rel} — skipped")
            continue
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        fps = float(cap.get(cv2.CAP_PROP_FPS)) or 0.0
        if total <= 0 or fps <= 0:
            print(f"WARNING: unknown geometry for {rel} — skipped")
            cap.release()
            continue
        for pos in positions:
            idx = min(total - 1, max(0, int(total * pos)))
            ts_ms = int(round(idx / fps * 1000))
            key = (rel, str(ts_ms))
            if key in existing:
                continue
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if not ok or frame is None:
                print(f"WARNING: frame {idx} of {rel} unreadable — skipped")
                continue
            dest_dir = out_dir / dataset_dir
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / f"{video.stem}__{ts_ms}ms.jpg"
            cv2.imwrite(str(dest), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
            counter += 1
            rows.append({
                "frame_id": f"FR{counter:06d}",
                "dataset_id": dataset_id,
                "source_video": video.name,
                "source_rel_path": rel,
                "timestamp_ms": str(ts_ms),
                "frame_file": dest.relative_to(root).as_posix(),
                "width": str(frame.shape[1]),
                "height": str(frame.shape[0]),
                "frame_sha256": _sha256(dest),
                "extraction_date": date.today().isoformat(),
                "tool": "catalog_frames.py cv2",
            })
            existing.add(key)
        cap.release()

    images = sorted(
        p for p in raw.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
        and "frame_catalog" not in p.parts
    )
    for image in images[::image_stride]:
        rel = image.relative_to(root).as_posix()
        key = (rel, "0")
        if key in existing:
            continue
        img = cv2.imread(str(image))
        if img is None:
            print(f"WARNING: image {rel} unreadable — skipped")
            continue
        dataset_dir = image.relative_to(raw).parts[0]
        dataset_id = DIR_TO_DATASET.get(dataset_dir, "SRC000")
        dest_dir = out_dir / dataset_dir
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{image.stem}__0ms.jpg"
        shutil.copyfile(image, dest)
        counter += 1
        rows.append({
            "frame_id": f"FR{counter:06d}",
            "dataset_id": dataset_id,
            "source_video": image.name,
            "source_rel_path": rel,
            "timestamp_ms": "0",
            "frame_file": dest.relative_to(root).as_posix(),
            "width": str(img.shape[1]),
            "height": str(img.shape[0]),
            "frame_sha256": _sha256(dest),
            "extraction_date": date.today().isoformat(),
            "tool": f"catalog_frames.py image-stride-{image_stride}",
        })
        existing.add(key)
    return rows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Catalog sample frames from raw videos")
    p.add_argument("--root", type=Path,
                   default=Path(__file__).resolve().parent.parent)
    p.add_argument("--positions", default="0.1,0.5,0.9",
                   help="comma-separated frame positions (0..1)")
    p.add_argument("--rebuild", action="store_true",
                   help="drop existing catalog and regenerate")
    p.add_argument("--image-stride", type=int, default=10,
                   help="keep every Nth static image (default: 10)")
    args = p.parse_args(argv)
    if args.image_stride < 1:
        raise SystemExit("ERROR: --image-stride must be >= 1")

    try:
        positions = [float(x) for x in args.positions.split(",")]
    except ValueError:
        raise SystemExit("ERROR: --positions must be comma-separated floats")
    if not positions or any(not 0.0 <= x < 1.0 for x in positions):
        raise SystemExit("ERROR: positions must be in [0.0, 1.0)")

    rows = catalog(args.root, positions, rebuild=args.rebuild,
                   image_stride=args.image_stride)
    out = args.root / "data" / "catalog" / "frame_samples.csv"
    _write_frames_csv(out, rows)
    by_ds: dict[str, int] = {}
    for r in rows:
        by_ds[r["dataset_id"]] = by_ds.get(r["dataset_id"], 0) + 1
    print(f"catalog: {len(rows)} frames -> {out}")
    print("  ", ", ".join(f"{k}={v}" for k, v in sorted(by_ds.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
