#!/usr/bin/env python3
"""NightEyes — two-annotator consolidation (protocol section 6, steps 5-8).

Compares independent annotations and consolidates the ground truth,
keeping divergences as UNCERTAIN (never as ABSENT).

    python scripts/merge_annotations.py --root . \
        --annotator-a ANN_1 --annotator-b ANN_2 \
        --consolidator AN_CONSOLIDATED

Matching (per session + participant + dataset + domain + behavior_code):
    * temporal overlap ratio >= 0.5 against the smaller episode -> pair
    * both PRESENT (same label)            -> consensus keeps the label
    * labels differ                        -> UNCERTAIN (divergence)
    * seen by only one annotator           -> UNCERTAIN (single observation)

Input:  data/annotation/episodes.csv (rows of both annotators)
Output: data/annotation/episodes_consolidated.csv + divergence report
        (swap into episodes.csv only after human review).
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

EPISODES_HEADER = [
    "episode_id", "session_id", "participant_id", "dataset_id", "start_ms",
    "end_ms", "domain", "behavior_code", "reference_label", "annotator_id",
    "annotation_confidence", "lighting_condition", "occlusion_condition",
    "annotation_notes",
]

REPORT_HEADER = [
    "group_key", "match_type", "annotator_a_episodes",
    "annotator_b_episodes", "consolidated_label", "detail",
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


def _overlap_ratio(a: dict, b: dict) -> float:
    s = max(int(a["start_ms"]), int(b["start_ms"]))
    e = min(int(a["end_ms"]), int(b["end_ms"]))
    inter = max(0, e - s)
    if inter == 0:
        return 0.0
    len_a = int(a["end_ms"]) - int(a["start_ms"])
    len_b = int(b["end_ms"]) - int(b["start_ms"])
    return inter / max(1, min(len_a, len_b))


def _group_key(ep: dict) -> tuple:
    return (
        ep["session_id"].strip(), ep["participant_id"].strip(),
        ep["dataset_id"].strip(), ep["domain"].strip(),
        (ep.get("behavior_code") or "").strip(),
    )


def merge(
    episodes: list[dict],
    annotator_a: str,
    annotator_b: str,
    consolidator: str,
) -> tuple[list[dict], list[dict]]:
    a_rows = [e for e in episodes if e["annotator_id"].strip() == annotator_a]
    b_rows = [e for e in episodes if e["annotator_id"].strip() == annotator_b]
    others = [
        e for e in episodes
        if e["annotator_id"].strip() not in (annotator_a, annotator_b)
    ]

    groups: dict[tuple, dict[str, list[dict]]] = {}
    for e in a_rows:
        groups.setdefault(_group_key(e), {"a": [], "b": []})["a"].append(e)
    for e in b_rows:
        groups.setdefault(_group_key(e), {"a": [], "b": []})["b"].append(e)

    consolidated: list[dict] = []
    report: list[dict] = []
    counter = 0

    def new_id() -> str:
        nonlocal counter
        counter += 1
        return f"EPC{counter:06d}"

    for key in sorted(groups, key=str):
        g = groups[key]
        a_list = sorted(g["a"], key=lambda x: int(x["start_ms"]))
        b_list = sorted(g["b"], key=lambda x: int(x["start_ms"]))
        paired_b: set[int] = set()

        for a in a_list:
            best, best_ratio, best_idx = None, 0.0, -1
            for i, b in enumerate(b_list):
                if i in paired_b:
                    continue
                r = _overlap_ratio(a, b)
                if r > best_ratio:
                    best, best_ratio, best_idx = b, r, i
            if best is not None and best_ratio >= 0.5:
                paired_b.add(best_idx)
                la = a["reference_label"].strip()
                lb = best["reference_label"].strip()
                if la == lb:
                    label, match, detail = la, "CONSENSUS", f"both={la}"
                else:
                    label = "UNCERTAIN"
                    match = "DIVERGENCE"
                    detail = f"A={la} B={lb} -> UNCERTAIN"
                row = dict(a)
                row["episode_id"] = new_id()
                row["reference_label"] = label
                row["annotator_id"] = consolidator
                row["annotation_notes"] = (
                    (a.get("annotation_notes") or "") +
                    f" | merged({annotator_a}+{annotator_b}): {detail}"
                ).strip(" |")
                consolidated.append(row)
                report.append({
                    "group_key": "|".join(str(x) for x in key),
                    "match_type": match,
                    "annotator_a_episodes": "1",
                    "annotator_b_episodes": "1",
                    "consolidated_label": label,
                    "detail": detail,
                })
            else:
                row = dict(a)
                row["episode_id"] = new_id()
                row["reference_label"] = "UNCERTAIN"
                row["annotator_id"] = consolidator
                row["annotation_notes"] = (
                    (a.get("annotation_notes") or "") +
                    " | merged: seen by annotator A only -> UNCERTAIN"
                ).strip(" |")
                consolidated.append(row)
                report.append({
                    "group_key": "|".join(str(x) for x in key),
                    "match_type": "SINGLE_A",
                    "annotator_a_episodes": "1",
                    "annotator_b_episodes": "0",
                    "consolidated_label": "UNCERTAIN",
                    "detail": f"only {annotator_a} observed this episode",
                })

        for i, b in enumerate(b_list):
            if i in paired_b:
                continue
            row = dict(b)
            row["episode_id"] = new_id()
            row["reference_label"] = "UNCERTAIN"
            row["annotator_id"] = consolidator
            row["annotation_notes"] = (
                (b.get("annotation_notes") or "") +
                " | merged: seen by annotator B only -> UNCERTAIN"
            ).strip(" |")
            consolidated.append(row)
            report.append({
                "group_key": "|".join(str(x) for x in key),
                "match_type": "SINGLE_B",
                "annotator_a_episodes": "0",
                "annotator_b_episodes": "1",
                "consolidated_label": "UNCERTAIN",
                "detail": f"only {annotator_b} observed this episode",
            })

    # Rows from other annotators pass through untouched (e.g. QUALITY notes)
    for e in others:
        row = dict(e)
        row["episode_id"] = new_id()
        consolidated.append(row)

    return consolidated, report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Consolidate two annotators")
    p.add_argument("--root", type=Path,
                   default=Path(__file__).resolve().parent.parent)
    p.add_argument("--annotator-a", required=True)
    p.add_argument("--annotator-b", required=True)
    p.add_argument("--consolidator", required=True)
    p.add_argument("--episodes", type=Path, default=None)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--report", type=Path, default=None)
    args = p.parse_args(argv)

    ep_path = args.episodes or (args.root / "data" / "annotation" / "episodes.csv")
    out_path = args.out or (
        args.root / "data" / "annotation" / "episodes_consolidated.csv")
    rep_path = args.report or (
        args.root / "data" / "quality_control" / "divergence_report.csv")

    episodes = _read(ep_path)
    if not episodes:
        raise SystemExit(f"ERROR: no episodes found at {ep_path}")

    ann_path = args.root / "data" / "annotation" / "annotators.csv"
    known = {a["annotator_id"].strip() for a in _read(ann_path)}
    for name in (args.annotator_a, args.annotator_b, args.consolidator):
        if name not in known:
            raise SystemExit(
                f"ERROR: annotator '{name}' not in annotators.csv "
                f"(available: {sorted(known) or 'none'})")

    consolidated, report = merge(
        episodes, args.annotator_a, args.annotator_b, args.consolidator)
    _write(out_path, EPISODES_HEADER, consolidated)
    _write(rep_path, REPORT_HEADER, report)

    counts: dict[str, int] = {}
    for r in report:
        counts[r["match_type"]] = counts.get(r["match_type"], 0) + 1
    print(f"consolidated {len(consolidated)} episodes -> {out_path}")
    print(f"divergence report -> {rep_path}")
    print("  ", ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    uncertain = sum(1 for e in consolidated
                    if e["reference_label"] == "UNCERTAIN")
    print(f"  UNCERTAIN kept: {uncertain} (never collapsed to ABSENT)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
