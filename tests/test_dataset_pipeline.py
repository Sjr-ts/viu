"""Tests for the consolidated supervised dataset pipeline (protocol §7-§10)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from evaluate_engine import evaluate
from make_facecrop_batch import main as facecrop_main
from validate_dataset import validate_project


SPLIT_HEADER = [
    "frame_id", "dataset_id", "participant_id", "session_id", "image_path",
    "frame_sha256", "timestamp_ms", "sleepiness_label", "sleepiness_behavior",
    "sleepiness_confidence", "distraction_label", "distraction_behavior",
    "distraction_confidence", "distraction_gaze", "phone_visible",
    "lighting_condition", "occlusion_condition", "face_visible",
    "annotation_notes", "split",
]


def _write(path: Path, header: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        w.writerows(rows)


def test_facecrop_batch_covers_three_domains(tmp_path):
    out = tmp_path / "batch.json"
    rc = facecrop_main([
        "--out", str(out),
        "--labels", "1=PRESENT:SLEEP_001,2=ABSENT",
    ])
    assert rc == 0
    rows = json.loads(out.read_text(encoding="utf-8"))
    assert len(rows) == 6
    assert {r["domain"] for r in rows} == {"FATIGUE", "SLEEPINESS", "DISTRACTION"}
    fatigue = next(r for r in rows if r["domain"] == "FATIGUE")
    assert fatigue["reference_label"] == "UNCERTAIN"
    distraction = next(r for r in rows if r["domain"] == "DISTRACTION")
    assert distraction["reference_label"] == "UNOBSERVABLE"
    assert all(r["face_visible"] == "YES" for r in rows)
    assert all(r["behavior_code"] == "" or r["behavior_code"] == "SLEEP_001" for r in rows)


def test_facecrop_batch_rejects_unsupported_positive_code(tmp_path):
    try:
        facecrop_main(["--out", str(tmp_path / "b.json"),
                       "--labels", "1=PRESENT:BOGUS"])
    except SystemExit as exc:
        assert "SLEEP" in str(exc)
    else:
        raise AssertionError("invalid behavior code must be rejected")


def test_evaluate_engine_without_scores_is_explicit(tmp_path):
    report = evaluate(tmp_path, None, 0.5)
    assert report["status"] == "NOT_EVALUATED"
    assert "reason" in report
    assert "independence_note" in report


def test_v21_flags_participant_in_two_splits(tmp_path):
    ann = tmp_path / "data" / "annotation"
    ann.mkdir(parents=True)
    (ann / "episodes.csv").write_text(
        "episode_id,session_id,participant_id,dataset_id,start_ms,end_ms,domain,"
        "behavior_code,reference_label,annotator_id,annotation_confidence,"
        "lighting_condition,occlusion_condition,annotation_notes\n",
        encoding="utf-8",
    )
    for split in ("train", "validation"):
        _write(tmp_path / "data" / "processed" / f"{split}.csv", SPLIT_HEADER, [{
            "frame_id": f"FR{split}", "dataset_id": "SRC003",
            "participant_id": "PT_SHARED", "session_id": "SS1",
            "image_path": "x.jpg", "frame_sha256": "0" * 64,
            "timestamp_ms": "0", "sleepiness_label": "ABSENT",
            "distraction_label": "ABSENT", "face_visible": "YES", "split": split,
        }])
    report = validate_project(tmp_path)
    assert any(i["check_id"] == "V21" and i["severity"] == "ERROR"
               for i in report.issues)


def test_v15_flags_filename_derived_episode(tmp_path):
    ann = tmp_path / "data" / "annotation"
    ann.mkdir(parents=True)
    (ann / "episodes.csv").write_text(
        "episode_id,session_id,participant_id,dataset_id,start_ms,end_ms,domain,"
        "behavior_code,reference_label,annotator_id,annotation_confidence,"
        "lighting_condition,occlusion_condition,annotation_notes\n"
        "EP1,SS1,PT1,SRC003,0,1000,SLEEPINESS,SLEEP_003,PRESENT,ANN_1,LOW,UNKNOWN,"
        "UNKNOWN,auto-derived from filename (low confidence draft)\n",
        encoding="utf-8",
    )
    report = validate_project(tmp_path)
    assert any(i["check_id"] == "V15" for i in report.issues)
