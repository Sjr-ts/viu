#!/usr/bin/env python3
"""NightEyes — Level B window builder (protocol section 3).

Derives temporal windows from annotated episodes (Level A).

    python scripts/make_windows.py --root . --window-ms 5000 \
        --annotator AN_CONSOLIDATED

Rules:
    * By default only windows overlapping a human annotated episode are emitted;
      no QUALITY domain and no fabricated ABSENT for unannotated material.
    * Window grid per session: 0 .. duration_ms, step = window_ms
      (last window may be partial if duration is not a multiple).
    * Window label priority: PRESENT > UNCERTAIN > UNOBSERVABLE > ABSENT.
      A window is PRESENT when any overlapping episode is PRESENT, etc.
    * UNCERTAIN/UNOBSERVABLE are never collapsed to ABSENT.
    * Original episode intervals are never modified (windows are a new
      derived artifact; episodes stay exactly as annotated).
    * The consolidator annotator MUST already exist in annotators.csv
      (validator V02 checks the reference).
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

LABEL_PRIORITY = {"ABSENT": 0, "UNOBSERVABLE": 1, "UNCERTAIN": 2, "PRESENT": 3}
ALL_DOMAINS = ("FATIGUE", "SLEEPINESS", "DISTRACTION", "QUALITY")
PROTOCOL_DOMAINS = ("FATIGUE", "SLEEPINESS", "DISTRACTION")
CONF_ORDER = {"": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}

WINDOWS_HEADER = [
    "window_id", "session_id", "participant_id", "dataset_id",
    "window_start_ms", "window_end_ms", "domain", "reference_label",
    "annotator_id", "annotation_confidence", "lighting_condition",
    "occlusion_condition", "annotation_notes",
]


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _write(path: Path, header: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def build_windows(
    root: Path,
    window_ms: int = 5000,
    annotator: str = "AN_CONSOLIDATED",
    domains: tuple[str, ...] = PROTOCOL_DOMAINS,
    annotated_only: bool = True,
) -> list[dict]:
    ann_dir = root / "data" / "annotation"
    sessions = _read(ann_dir / "sessions.csv")
    episodes = _read(ann_dir / "episodes.csv")
    annotators = _read(ann_dir / "annotators.csv")

    if not sessions:
        raise SystemExit("ERROR: data/annotation/sessions.csv is empty — "
                         "register sessions before building windows.")
    known = {a["annotator_id"].strip() for a in annotators}
    if annotator not in known:
        raise SystemExit(
            f"ERROR: annotator '{annotator}' not found in annotators.csv "
            f"(available: {sorted(known) or 'none'}). Register the "
            "consolidator first — validator V02 enforces this reference."
        )
    if window_ms <= 0:
        raise SystemExit("ERROR: --window-ms must be > 0")

    # Index episodes by (session, domain)
    by_key: dict[tuple[str, str], list[dict]] = {}
    for ep in episodes:
        key = (ep["session_id"].strip(), ep["domain"].strip())
        by_key.setdefault(key, []).append(ep)

    rows: list[dict] = []
    counter = 0
    for sess in sessions:
        sid = sess["session_id"].strip()
        pid = sess["participant_id"].strip()
        did = sess["dataset_id"].strip()
        try:
            duration = int(sess["duration_ms"])
        except (KeyError, ValueError):
            raise SystemExit(f"ERROR: session {sid} has invalid duration_ms")
        if duration <= 0:
            continue

        for domain in domains:
            eps = sorted(
                by_key.get((sid, domain), []),
                key=lambda e: int(e["start_ms"]),
            )
            if annotated_only and not eps:
                continue
            starts = range(0, duration, window_ms)
            for start in starts:
                end = min(start + window_ms, duration)
                if end <= start:
                    continue
                overlapping = [
                    e for e in eps
                    if int(e["start_ms"]) < end and int(e["end_ms"]) > start
                ]
                if annotated_only and not overlapping:
                    continue
                label = "ABSENT"
                if overlapping:
                    label = max(
                        (e["reference_label"].strip() for e in overlapping),
                        key=lambda lb: LABEL_PRIORITY.get(lb, -1),
                    )
                confidence = ""
                if overlapping:
                    confidence = max(
                        (e.get("annotation_confidence", "").strip()
                         for e in overlapping),
                        key=lambda c: CONF_ORDER.get(c, 0),
                    )
                counter += 1
                notes = (
                    "auto-derived level-B window; episodes: "
                    + ",".join(e["episode_id"] for e in overlapping)
                    if overlapping
                    else "auto-derived level-B window; no episode overlap"
                )
                rows.append({
                    "window_id": f"W{counter:06d}",
                    "session_id": sid,
                    "participant_id": pid,
                    "dataset_id": did,
                    "window_start_ms": str(start),
                    "window_end_ms": str(end),
                    "domain": domain,
                    "reference_label": label,
                    "annotator_id": annotator,
                    "annotation_confidence": confidence,
                    "lighting_condition": sess.get("lighting_condition", ""),
                    "occlusion_condition": sess.get("occlusion_condition", ""),
                    "annotation_notes": notes,
                })
    return rows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Build Level B windows from episodes")
    p.add_argument("--root", type=Path,
                   default=Path(__file__).resolve().parent.parent)
    p.add_argument("--window-ms", type=int, default=5000,
                   help="window size in ms (protocol initial value: 5000)")
    p.add_argument("--annotator", default="AN_CONSOLIDATED",
                   help="consolidator annotator_id (must exist in annotators.csv)")
    p.add_argument("--annotated-only", action="store_true", default=True,
                   help="emit only windows supported by a human annotated episode "
                        "(default; never fabricate ABSENT)")
    p.add_argument("--include-unannotated", dest="annotated_only",
                   action="store_false",
                   help="include full grid with synthetic ABSENT (legacy behavior)")
    p.add_argument("--out", type=Path, default=None,
                   help="output CSV (default: data/annotation/windows.csv)")
    args = p.parse_args(argv)

    rows = build_windows(args.root, args.window_ms, args.annotator,
                         annotated_only=args.annotated_only)
    out = args.out or (args.root / "data" / "annotation" / "windows.csv")
    _write(out, WINDOWS_HEADER, rows)
    by_label: dict[str, int] = {}
    for r in rows:
        by_label[r["reference_label"]] = by_label.get(r["reference_label"], 0) + 1
    print(f"wrote {len(rows)} windows -> {out}")
    print("  labels:", ", ".join(f"{k}={v}" for k, v in sorted(by_label.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
