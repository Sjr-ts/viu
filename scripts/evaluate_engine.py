#!/usr/bin/env python3
"""NightEyes — offline Risk Engine evaluation (protocol §10).

The engine output is read ONLY after the ground truth is frozen. Engine
scores are never used to create or edit reference labels (protocol §7).

    python scripts/evaluate_engine.py --root . --scores data/reports/engine_scores.csv

Engine scores CSV (one row per frame/domain):
    frame_id,domain,score,predicted_label[,detection_start_ms]

If no scores file is supplied, a NOT_EVALUATED report is generated so the
absence of evaluation is explicit instead of silently implied by a PASS.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

DOMAINS = ("FATIGUE", "SLEEPINESS", "DISTRACTION")
POSITIVE = "PRESENT"
EXCLUDED = {"UNCERTAIN", "UNOBSERVABLE"}


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _binary_metrics(pairs: list[tuple[bool, bool]]) -> dict:
    tp = sum(1 for ref, pred in pairs if ref and pred)
    fp = sum(1 for ref, pred in pairs if not ref and pred)
    tn = sum(1 for ref, pred in pairs if not ref and not pred)
    fn = sum(1 for ref, pred in pairs if ref and not pred)
    sens = tp / (tp + fn) if tp + fn else None
    spec = tn / (tn + fp) if tn + fp else None
    prec = tp / (tp + fp) if tp + fp else None
    f1 = 2 * prec * sens / (prec + sens) if prec and sens else None
    return {
        "TP": tp, "FP": fp, "TN": tn, "FN": fn,
        "sensitivity": sens, "specificity": spec,
        "precision": prec, "f1": f1,
        "confusion_matrix": {"TP": tp, "FP": fp, "TN": tn, "FN": fn},
    }


def evaluate(root: Path, scores_path: Path | None, threshold: float) -> dict:
    processed = root / "data" / "processed"
    truth: dict[tuple[str, str], str] = {}
    condition: dict[tuple[str, str], dict] = {}
    for split in ("train", "validation", "test"):
        for row in _read(processed / f"{split}.csv"):
            condition[(row["frame_id"], "SLEEPINESS")] = {
                "lighting": row.get("lighting_condition", ""),
                "occlusion": row.get("occlusion_condition", ""),
                "face_visible": row.get("face_visible", ""),
                "split": split,
            }
            condition[(row["frame_id"], "DISTRACTION")] = condition[(row["frame_id"], "SLEEPINESS")]
            condition[(row["frame_id"], "FATIGUE")] = condition[(row["frame_id"], "SLEEPINESS")]
            truth[(row["frame_id"], "SLEEPINESS")] = row.get("sleepiness_label", "")
            truth[(row["frame_id"], "DISTRACTION")] = row.get("distraction_label", "")
            truth[(row["frame_id"], "FATIGUE")] = "UNCERTAIN"

    report = {
        "protocol": "NightEyes V0.1 §10",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scores_file": str(scores_path) if scores_path else None,
        "threshold": threshold,
        "ground_truth_frames": len({k[0] for k in truth}),
        "independence_note": "reference labels frozen before engine scores were read (§7)",
        "status": "NOT_EVALUATED",
        "per_domain": {},
        "excluded_from_binary_metrics": {},
        "by_capture_condition": {},
        "latency": {},
    }

    if scores_path is None or not scores_path.exists():
        report["reason"] = "no engine score file supplied; evaluation pending"
        return report

    scores = _read(scores_path)
    excluded: dict[str, int] = defaultdict(int)
    pairs: dict[str, list[tuple[bool, bool]]] = defaultdict(list)
    latency: dict[str, list[int]] = defaultdict(list)
    strata: dict[tuple[str, str], list[tuple[bool, bool]]] = defaultdict(list)

    for row in scores:
        key = (row["frame_id"], row["domain"])
        ref = truth.get(key, "")
        if not ref:
            continue
        if ref in EXCLUDED:
            excluded[row["domain"]] += 1
            continue
        if row["domain"] not in DOMAINS:
            continue
        try:
            score = float(row["score"])
        except (TypeError, ValueError):
            continue
        pred = score >= threshold
        if row.get("predicted_label"):
            pred = row["predicted_label"].strip() == POSITIVE
        pair = (ref == POSITIVE, pred)
        pairs[row["domain"]].append(pair)
        cond = condition.get(key, {})
        for field in ("lighting", "occlusion", "face_visible", "split"):
            strata[(row["domain"], f"{field}={cond.get(field, 'UNKNOWN')}")].append(pair)
        if row.get("detection_start_ms") and ref == POSITIVE and pred:
            latency[row["domain"]].append(int(row["detection_start_ms"]))

    for domain in DOMAINS:
        report["per_domain"][domain] = _binary_metrics(pairs[domain]) if pairs[domain] else None
        vals = latency[domain]
        report["latency"][domain] = {
            "n": len(vals),
            "mean_detection_start_ms": sum(vals) / len(vals) if vals else None,
        }
    report["excluded_from_binary_metrics"] = dict(excluded)
    report["by_capture_condition"] = {
        f"{domain}|{key}": _binary_metrics(vals)
        for (domain, key), vals in sorted(strata.items()) if vals
    }
    report["status"] = "EVALUATED" if any(pairs.values()) else "NOT_EVALUATED"
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Evaluate Risk Engine against frozen ground truth")
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--scores", type=Path, default=None)
    ap.add_argument("--threshold", type=float, default=0.5)
    args = ap.parse_args(argv)
    root = args.root.resolve()

    report = evaluate(root, args.scores, args.threshold)
    out = root / "data" / "reports"
    out.mkdir(parents=True, exist_ok=True)
    (out / "engine_evaluation.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    rows = [
        {"domain": domain, **metrics}
        for domain, metrics in report["per_domain"].items() if metrics
    ]
    with (out / "engine_evaluation.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=[
            "domain", "TP", "FP", "TN", "FN", "sensitivity", "specificity",
            "precision", "f1",
        ])
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in writer.fieldnames})
    print(f"engine evaluation: {report['status']} -> {out.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
