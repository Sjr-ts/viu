"""Tests for annotation tooling: make_windows, merge_annotations, catalog_frames."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

from make_windows import build_windows, main as windows_main
from merge_annotations import merge
from catalog_frames import catalog, FRAME_HEADER

# ---------------------------------------------------------------------------
# Fixture helpers (minimal project for annotation tools)
# ---------------------------------------------------------------------------

SESSIONS_HEADER = [
    "session_id", "participant_id", "dataset_id", "original_session_id",
    "video_filename", "duration_ms", "original_fps", "resolution",
    "lighting_condition", "camera_position", "glasses_condition",
    "occlusion_condition", "activity_type",
]

EPISODES_HEADER = [
    "episode_id", "session_id", "participant_id", "dataset_id", "start_ms",
    "end_ms", "domain", "behavior_code", "reference_label", "annotator_id",
    "annotation_confidence", "lighting_condition", "occlusion_condition",
    "annotation_notes",
]

ANNOTATORS_HEADER = [
    "annotator_id", "name", "training_status",
    "independent_annotation_enabled", "access_to_engine_scores", "notes",
]


def _write(path: Path, header: list, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        if rows and isinstance(rows[0], dict):
            w = csv.DictWriter(fh, fieldnames=header)
            w.writeheader()
            w.writerows(rows)
        else:
            w = csv.writer(fh)
            w.writerow(header)
            w.writerows(rows)


def _project(tmp_path: Path) -> Path:
    ann = tmp_path / "data" / "annotation"
    _write(ann / "sessions.csv", SESSIONS_HEADER, [
        ["SS1", "PT1", "SRC003", "sess_01", "video1.avi", "15000", "30",
         "640x480", "day", "dash", "no", "none", "driving"],
    ])
    _write(ann / "annotators.csv", ANNOTATORS_HEADER, [
        ["ANN_1", "A", "TRAINED", "YES", "NO", ""],
        ["ANN_2", "B", "TRAINED", "YES", "NO", ""],
        ["AN_CONSOLIDATED", "C", "TRAINED", "YES", "NO", ""],
    ])
    _write(ann / "episodes.csv", EPISODES_HEADER, [])
    return tmp_path


def _ep(eid, start, end, label, annotator, domain="SLEEPINESS",
        behavior="SLEEP_001", conf="HIGH"):
    row = [eid, "SS1", "PT1", "SRC003", str(start), str(end), domain,
           behavior, label, annotator, conf, "day", "none", ""]
    return dict(zip(EPISODES_HEADER, row))


# ---------------------------------------------------------------------------
# make_windows (Level B, protocol section 3)
# ---------------------------------------------------------------------------

def test_make_windows_labels(tmp_path):
    root = _project(tmp_path)
    _write(root / "data" / "annotation" / "episodes.csv", EPISODES_HEADER, [
        _ep("EP1", 1000, 6000, "PRESENT", "ANN_1"),
        _ep("EP2", 12000, 14000, "UNCERTAIN", "ANN_1"),
    ])
    rows = build_windows(root, window_ms=5000, annotator="AN_CONSOLIDATED")
    sleepy = [r for r in rows if r["domain"] == "SLEEPINESS"]
    assert len(sleepy) == 3  # 0-5000, 5000-10000, 10000-15000
    assert sleepy[0]["reference_label"] == "PRESENT"
    assert sleepy[1]["reference_label"] == "PRESENT"  # overlaps 5000-6000
    assert sleepy[2]["reference_label"] == "UNCERTAIN"  # 12000-14000
    # other domains default to ABSENT
    fatigue = [r for r in rows if r["domain"] == "FATIGUE"]
    assert all(r["reference_label"] == "ABSENT" for r in fatigue)


def test_make_windows_priority_present_over_uncertain(tmp_path):
    root = _project(tmp_path)
    _write(root / "data" / "annotation" / "episodes.csv", EPISODES_HEADER, [
        _ep("EP1", 0, 5000, "UNCERTAIN", "ANN_1", behavior="SLEEP_002"),
        _ep("EP2", 2000, 4000, "PRESENT", "ANN_1", behavior="SLEEP_001"),
    ])
    rows = build_windows(root, window_ms=5000, annotator="AN_CONSOLIDATED")
    w0 = next(r for r in rows
              if r["domain"] == "SLEEPINESS" and r["window_start_ms"] == "0")
    assert w0["reference_label"] == "PRESENT"


def test_make_windows_never_collapses_uncertain(tmp_path):
    root = _project(tmp_path)
    _write(root / "data" / "annotation" / "episodes.csv", EPISODES_HEADER, [
        _ep("EP1", 0, 5000, "UNCERTAIN", "ANN_1"),
        _ep("EP2", 5000, 10000, "UNOBSERVABLE", "ANN_1"),
    ])
    rows = build_windows(root, window_ms=5000, annotator="AN_CONSOLIDATED",
                         annotated_only=False)
    labels = [r["reference_label"] for r in rows
              if r["domain"] == "SLEEPINESS"]
    assert labels == ["UNCERTAIN", "UNOBSERVABLE", "ABSENT"]


def test_make_windows_default_never_fabricates(tmp_path):
    root = _project(tmp_path)
    _write(root / "data" / "annotation" / "episodes.csv", EPISODES_HEADER, [
        _ep("EP1", 0, 5000, "PRESENT", "ANN_1"),
    ])
    rows = build_windows(root, window_ms=5000, annotator="AN_CONSOLIDATED")
    assert rows
    assert {r["domain"] for r in rows} == {"SLEEPINESS"}
    assert all(r["reference_label"] != "ABSENT" for r in rows)


def test_make_windows_rejects_unknown_annotator(tmp_path):
    root = _project(tmp_path)
    with pytest.raises(SystemExit):
        build_windows(root, window_ms=5000, annotator="GHOST")


def test_make_windows_writes_valid_grid(tmp_path):
    root = _project(tmp_path)
    rows = build_windows(root, window_ms=5000, annotator="AN_CONSOLIDATED",
                         annotated_only=False)
    # grid covers session duration with no overlaps per (session, domain)
    for domain in {r["domain"] for r in rows}:
        ws = sorted((r for r in rows if r["domain"] == domain),
                    key=lambda r: int(r["window_start_ms"]))
        prev_end = 0
        for w in ws:
            assert int(w["window_start_ms"]) == prev_end
            assert int(w["window_end_ms"]) > int(w["window_start_ms"])
            prev_end = int(w["window_end_ms"])
        assert prev_end == 15000
    # ids unique
    ids = [r["window_id"] for r in rows]
    assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# merge_annotations (protocol section 6, steps 5-8)
# ---------------------------------------------------------------------------

def test_merge_consensus_keeps_label():
    eps = [
        _ep("EP1", 0, 5000, "PRESENT", "ANN_1"),
        _ep("EP2", 500, 4500, "PRESENT", "ANN_2"),
    ]
    cons, rep = merge(eps, "ANN_1", "ANN_2", "AN_CONSOLIDATED")
    assert len(cons) == 1
    assert cons[0]["reference_label"] == "PRESENT"
    assert cons[0]["annotator_id"] == "AN_CONSOLIDATED"
    assert rep[0]["match_type"] == "CONSENSUS"


def test_merge_divergence_becomes_uncertain():
    eps = [
        _ep("EP1", 0, 5000, "PRESENT", "ANN_1"),
        _ep("EP2", 0, 5000, "ABSENT", "ANN_2"),
    ]
    cons, rep = merge(eps, "ANN_1", "ANN_2", "AN_CONSOLIDATED")
    assert len(cons) == 1
    assert cons[0]["reference_label"] == "UNCERTAIN"  # never ABSENT
    assert rep[0]["match_type"] == "DIVERGENCE"


def test_merge_single_annotator_becomes_uncertain():
    eps = [_ep("EP1", 0, 5000, "PRESENT", "ANN_1")]
    cons, rep = merge(eps, "ANN_1", "ANN_2", "AN_CONSOLIDATED")
    assert len(cons) == 1
    assert cons[0]["reference_label"] == "UNCERTAIN"
    assert rep[0]["match_type"] == "SINGLE_A"


def test_merge_disjoint_episodes_are_single():
    eps = [
        _ep("EP1", 0, 1000, "PRESENT", "ANN_1"),
        _ep("EP2", 8000, 9000, "PRESENT", "ANN_2"),
    ]
    cons, rep = merge(eps, "ANN_1", "ANN_2", "AN_CONSOLIDATED")
    assert len(cons) == 2
    assert all(c["reference_label"] == "UNCERTAIN" for c in cons)


# ---------------------------------------------------------------------------
# catalog_frames (image inventory with SHA-256)
# ---------------------------------------------------------------------------

def _make_video(path: Path, frames: int = 30) -> None:
    import numpy as np
    import cv2
    path.parent.mkdir(parents=True, exist_ok=True)
    vw = cv2.VideoWriter(str(path),
                         cv2.VideoWriter_fourcc(*"MJPG"), 10.0, (64, 48))
    assert vw.isOpened(), "VideoWriter failed to open"
    for i in range(frames):
        img = np.full((48, 64, 3), i * 8 % 255, dtype="uint8")
        vw.write(img)
    vw.release()


def test_catalog_frames_extracts_and_hashes(tmp_path):
    video = tmp_path / "data" / "raw" / "YawDD" / "clip.avi"
    _make_video(video, frames=30)
    rows = catalog(tmp_path, positions=[0.5])
    assert len(rows) == 1
    r = rows[0]
    assert r["dataset_id"] == "SRC003"
    assert len(r["frame_sha256"]) == 64
    frame_path = tmp_path / r["frame_file"]
    assert frame_path.exists()
    assert r["width"] == "64" and r["height"] == "48"


def test_catalog_frames_idempotent(tmp_path):
    video = tmp_path / "data" / "raw" / "YawDD" / "clip.avi"
    _make_video(video, frames=30)
    first = catalog(tmp_path, positions=[0.5])
    # persist catalog, then re-run: same (video, timestamp) must be skipped
    csv_path = tmp_path / "data" / "catalog" / "frame_samples.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FRAME_HEADER)
        w.writeheader()
        w.writerows(first)
    second = catalog(tmp_path, positions=[0.5])
    assert len(first) == 1
    assert len(second) == 1  # no duplicate for same (video, timestamp)


def test_catalog_frames_no_videos_is_safe(tmp_path):
    rows = catalog(tmp_path, positions=[0.5])
    assert rows == []
