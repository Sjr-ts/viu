#!/usr/bin/env python3
"""Build a 3-domain annotation batch for still face-crop frames.

    python scripts/make_facecrop_batch.py --out data/annotation/_batch_097.json \
        --labels "1164=ABSENT,1165=ABSENT,1166=PRESENT:SLEEP_001"

Eye state is supplied by the human reviewer after visual inspection of the
review sheet. FATIGUE is always UNCERTAIN (a single frame cannot establish
blink-rate change or persistence) and DISTRACTION is UNOBSERVABLE (the crop
removes the driving scene needed to judge attention deviation).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Generate face-crop annotation batch")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--labels", required=True,
                    help="comma-separated idx=LABEL[:BEHAVIOR] entries")
    args = ap.parse_args(argv)

    rows = []
    for item in args.labels.split(","):
        item = item.strip()
        if not item:
            continue
        idx, spec = item.split("=", 1)
        parts = spec.split(":", 1)
        label = parts[0].strip()
        code = parts[1].strip() if len(parts) > 1 else ""
        if label == "PRESENT" and code not in ("SLEEP_001", "SLEEP_003"):
            raise SystemExit(f"PRESENT requires SLEEP_001/SLEEP_003 for frame {idx}")
        base = {
            "idx": int(idx),
            "phone_visible": "UNKNOWN",
            "annotation_confidence": "HIGH" if label in ("PRESENT", "ABSENT") else "MEDIUM",
            "lighting_condition": "UNVERIFIED_GRAYSCALE",
            "occlusion_condition": "GLASSES",
            "face_visible": "YES",
        }
        rows.append(dict(base, domain="FATIGUE", reference_label="UNCERTAIN",
                         behavior_code="", gaze_direction="",
                         annotation_notes="single frame: blink-rate change/persistence not assessable"))
        rows.append(dict(base, domain="SLEEPINESS", reference_label=label,
                         behavior_code=code, gaze_direction="",
                         annotation_notes=f"human visual eye-state assessment of catalog frame #{idx}"))
        rows.append(dict(base, domain="DISTRACTION", reference_label="UNOBSERVABLE",
                         behavior_code="", gaze_direction="",
                         annotation_notes="face crop removes driving scene; attention deviation not assessable"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} rows for {len(rows)//3} frames -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
