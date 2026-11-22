#!/usr/bin/env python3
"""Enrich frame annotations with explicit per-image detection labels.

    python scripts/enrich_frame_labels.py --root .

Adds (protocol §2.3 / §9 and Victor's 2026-11-21 requirements):
    activity_label   TALKING | YAWNING | PHONE_USE | NEUTRAL | UNKNOWN
    phone_detection  YES | NO | UNKNOWN  (visual phone detection)
    face_detection   YES | PARTIAL | NO | UNKNOWN  (visual face detection)

Values are derived ONLY from the human visual notes already recorded in
frame_annotations.csv (never from engine scores or source filenames).
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

FRAME_HEADER = [
    "frame_id", "dataset_id", "source_video", "participant_id", "session_id",
    "timestamp_ms", "domain", "reference_label", "behavior_code",
    "gaze_direction", "phone_visible", "annotator_id", "annotation_confidence",
    "lighting_condition", "occlusion_condition", "face_visible",
    "annotation_notes", "activity_label", "phone_detection", "face_detection",
]


def activity_from(notes: str, code: str, label: str, phone: str) -> str:
    notes = notes.lower()
    if phone == "YES" or "phone visible" in notes or "phone-like" in notes \
            or "held in hand" in notes:
        return "PHONE_USE"
    if code == "SLEEP_003" or "yawn" in notes:
        return "YAWNING"
    if code in ("SLEEP_001", "SLEEP_006") and label == "PRESENT":
        return "DROWSY"
    if "talking" in notes or "smiling" in notes or "mouth open" in notes:
        return "TALKING"
    if "mouth closed" in notes or "eyes open" in notes \
            or "no visible yawn" in notes or "no clear yawn" in notes:
        return "NEUTRAL"
    if "sunglasses" in notes:
        return "NEUTRAL"
    return "UNKNOWN"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Enrich frame annotations")
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = ap.parse_args(argv)
    path = args.root.resolve() / "data" / "annotation" / "frame_annotations.csv"
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    observations: dict[str, dict] = {}
    for row in rows:
        if row["domain"] == "SLEEPINESS":
            observations[row["frame_id"]] = row
    for row in rows:
        obs = observations.get(row["frame_id"], row)
        row["activity_label"] = activity_from(
            obs.get("annotation_notes") or "",
            obs.get("behavior_code") or "",
            obs.get("reference_label") or "",
            obs.get("phone_visible") or "",
        )
        row["phone_detection"] = (row.get("phone_visible") or "UNKNOWN").strip()
        row["face_detection"] = (row.get("face_visible") or "UNKNOWN").strip()
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FRAME_HEADER)
        w.writeheader()
        w.writerows(rows)
    print(f"enriched {len(rows)} annotation rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
