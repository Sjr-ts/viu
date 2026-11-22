#!/usr/bin/env python3
"""Record human verification of phone-candidate frames (protocol §2.3).

    python scripts/record_phone_verification.py --root . \
        --spec "14=YES,15=YES,17=YES,18=YES,22=YES,24=YES,25=YES,30=YES,31=YES,32=YES,33=YES,43=YES,47=YES"

Candidates are indexed P#0..P#N in the order they appear in frame_samples.csv.
The source YOLO class was used only to select candidates; phone_detection is
set here from human visual inspection.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

HEADER = [
    "frame_id", "dataset_id", "source_video", "participant_id", "session_id",
    "timestamp_ms", "domain", "reference_label", "behavior_code",
    "gaze_direction", "phone_visible", "annotator_id", "annotation_confidence",
    "lighting_condition", "occlusion_condition", "face_visible",
    "annotation_notes", "activity_label", "phone_detection", "face_detection",
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Record phone verification")
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--spec", required=True, help="P#index=YES|NO|UNKNOWN, ...")
    args = ap.parse_args(argv)
    root = args.root.resolve()
    catalog_path = root / "data" / "catalog" / "frame_samples.csv"
    ann_path = root / "data" / "annotation" / "frame_annotations.csv"

    with catalog_path.open(newline="", encoding="utf-8") as fh:
        candidates = [r for r in csv.DictReader(fh)
                      if r["tool"].startswith("phone_candidate")]
    with ann_path.open(newline="", encoding="utf-8") as fh:
        existing = list(csv.DictReader(fh))
    done = {(r["frame_id"], r["domain"]) for r in existing}

    decisions: dict[int, str] = {}
    for item in args.spec.split(","):
        item = item.strip()
        if not item:
            continue
        idx, value = item.split("=")
        decisions[int(idx)] = value.strip()

    added = 0
    for idx, row in enumerate(candidates):
        phone = decisions.get(idx, "UNKNOWN")
        if phone not in {"YES", "NO", "UNKNOWN"}:
            raise SystemExit(f"invalid decision for P#{idx}: {phone}")
        looking_at_phone = idx in {32, 33}
        for domain in ("FATIGUE", "SLEEPINESS", "DISTRACTION"):
            key = (row["frame_id"], domain)
            if key in done:
                continue
            if domain == "FATIGUE":
                label, code, gaze = "UNCERTAIN", "", ""
                note = "single frame: blink-rate change/persistence not assessable"
            elif domain == "SLEEPINESS":
                label, code, gaze = "ABSENT", "", ""
                note = f"human visual verification of phone candidate P#{idx}; eyes open"
            else:
                label = "UNCERTAIN" if looking_at_phone else "ABSENT"
                code = "DIST_005" if looking_at_phone else ""
                gaze = "DOWN" if looking_at_phone else ""
                note = ("gaze directed toward phone screen; persistence unknown"
                        if looking_at_phone else
                        "phone presence/object in frame alone is not distraction PRESENT (§2.3)")
            existing.append({
                "frame_id": row["frame_id"], "dataset_id": row["dataset_id"],
                "source_video": row["source_video"], "participant_id": "UNKNOWN",
                "session_id": "UNKNOWN", "timestamp_ms": row["timestamp_ms"],
                "domain": domain, "reference_label": label, "behavior_code": code,
                "gaze_direction": gaze, "phone_visible": phone,
                "annotator_id": "ANN_1", "annotation_confidence": "MEDIUM",
                "lighting_condition": "UNVERIFIED_GRAYSCALE",
                "occlusion_condition": "NONE", "face_visible": "YES",
                "annotation_notes": note,
                "activity_label": "PHONE_USE" if phone == "YES" else "NEUTRAL",
                "phone_detection": phone, "face_detection": "YES",
            })
            added += 1

    with ann_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=HEADER)
        w.writeheader()
        w.writerows(existing)
    yes = sum(1 for i in decisions.values() if i == "YES")
    print(f"verified {len(decisions)} candidates ({yes} phone YES); added {added} annotation rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
