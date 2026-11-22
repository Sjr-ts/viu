#!/usr/bin/env python3
"""Append human frame-level annotations (Level-A units at frame timestamps).

Usage:
    python scripts/record_frame_annotations.py --batch annotations_batch.json
    python scripts/record_frame_annotations.py --index 0,1,2 --domain SLEEPINESS --label ABSENT

Batch JSON: list of dicts with keys:
    idx (int, catalog row index), domain, reference_label, behavior_code,
    gaze_direction, phone_visible, annotation_confidence, annotation_notes
"""
import argparse
import csv
import json
from pathlib import Path

CATALOG = Path("data/catalog/frame_samples.csv")
OUT = Path("data/annotation/frame_annotations.csv")
HEADER = [
    "frame_id", "dataset_id", "source_video", "participant_id", "session_id",
    "timestamp_ms", "domain", "reference_label", "behavior_code",
    "gaze_direction", "phone_visible", "annotator_id", "annotation_confidence",
    "lighting_condition", "occlusion_condition", "face_visible", "annotation_notes",
    "activity_label", "phone_detection", "face_detection",
]

VALID_LABELS = {"PRESENT", "ABSENT", "UNCERTAIN", "UNOBSERVABLE"}
VALID_DOMAINS = {"FATIGUE", "SLEEPINESS", "DISTRACTION"}


def participant_from_video(video_stem: str) -> str:
    head = video_stem.split("-", 1)[0]
    return f"YD_P{head}" if head.isdigit() else f"YD_{head}"


def identity_for_row(row: dict, frame_stem: str) -> tuple[str, str]:
    stem = frame_stem.rsplit("__", 1)[0]
    if row["dataset_id"] == "SRC009":
        parts = row["source_rel_path"].split("/")
        split = parts[-3].upper() if len(parts) >= 3 else "UNK"
        head = stem.split("_jpg.")[0]
        return f"D9_{head}", f"D9_{split}"
    return participant_from_video(stem), stem


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", required=True, help="JSON file with list of annotation dicts")
    args = ap.parse_args()

    catalog = list(csv.DictReader(CATALOG.open(encoding="utf-8")))
    batch = json.loads(Path(args.batch).read_text(encoding="utf-8"))
    if not OUT.exists():
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(HEADER)

    existing = set()
    if OUT.exists():
        for r in csv.DictReader(OUT.open(encoding="utf-8")):
            existing.add((r["frame_id"], r["domain"]))

    written = 0
    with OUT.open("a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        for item in batch:
            idx = int(item["idx"])
            row = catalog[idx]
            stem = Path(row.get("original_frame_file") or row["frame_file"]).stem
            participant_id, session_id = identity_for_row(row, stem)
            key = (row["frame_id"], item["domain"])
            if key in existing:
                continue
            if item["domain"] not in VALID_DOMAINS:
                raise SystemExit(f"invalid domain: {item['domain']}")
            if item["reference_label"] not in VALID_LABELS:
                raise SystemExit(f"invalid label: {item['reference_label']}")
            w.writerow([
                row["frame_id"], row["dataset_id"], row["source_video"],
                participant_id, session_id,
                row["timestamp_ms"], item["domain"], item["reference_label"],
                item.get("behavior_code", ""), item.get("gaze_direction", ""),
                item.get("phone_visible", ""), item.get("annotator_id", "ANN_1"),
                item.get("annotation_confidence", "MEDIUM"),
                item.get("lighting_condition", "UNKNOWN"),
                item.get("occlusion_condition", "UNKNOWN"),
                item.get("face_visible", "UNKNOWN"),
                item.get("annotation_notes", ""),
                item.get("activity_label", "UNKNOWN"),
                item.get("phone_detection", "UNKNOWN"),
                item.get("face_detection", "UNKNOWN"),
            ])
            written += 1
    print(f"wrote {written} rows ({len(batch)} in batch, dups skipped)")


if __name__ == "__main__":
    main()
