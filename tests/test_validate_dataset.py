"""Automated tests for scripts/validate_dataset.py.

Each test builds a minimal valid project fixture and then introduces a
specific defect to verify that the corresponding check reports it.
"""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import pytest

from validate_dataset import validate_project

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

DATASETS_HEADER = [
    "dataset_id", "dataset_name", "primary_domain", "institution",
    "official_url", "publication_url", "access_url", "participants_count",
    "videos_count", "duration_hours", "original_resolution",
    "original_fps", "camera_type", "available_modalities",
    "original_annotation_format", "license", "commercial_usage",
    "redistribution_permission", "derivative_work_permission",
    "access_status", "verification_date", "source_notes",
]

DATASET_ROW = [
    "SRC001", "TEST-DS", "MULTI_DOMAIN", "Test Institution",
    "https://example.org", "https://example.org/pub",
    "https://example.org/access", "10", "20", "1.0",
    "640x480", "30", "test camera", "RGB", "test format",
    "TEST-LICENSE", "UNKNOWN", "UNKNOWN", "UNKNOWN",
    "AVAILABLE", "2026-11-19", "test notes",
]

COMPAT_HEADER = [
    "dataset_id", "source_label", "source_label_definition", "mapped_domain",
    "mapped_behavior", "compatibility_level", "mapping_method",
    "temporal_resolution", "requires_reannotation", "reviewer_notes",
]

COMPAT_ROW = [
    "SRC001", "drowsy", "test drowsy label", "SLEEPINESS", "SLEEP_001",
    "PARTIAL", "test method", "session-level", "YES", "note",
]

LICENSES_HEADER = [
    "dataset_id", "license_name", "license_url", "license_source",
    "commercial_usage", "redistribution_permission",
    "derivative_work_permission", "permission_required",
    "verification_date", "license_notes",
]

LICENSE_ROW = [
    "SRC001", "TEST", "https://example.org/lic", "test source",
    "UNKNOWN", "UNKNOWN", "UNKNOWN", "NO", "2026-11-19", "note",
]

SOURCES_HEADER = [
    "source_file_id", "dataset_id", "original_filename", "original_path",
    "checksum_sha256", "file_type", "file_size", "import_date",
    "access_permission", "processing_status",
]

PARTICIPANTS_HEADER = [
    "participant_id", "dataset_id", "original_participant_id",
    "anonymized_id", "consent_status", "demographic_metadata_availability",
]

PARTICIPANT_ROW = [
    "PT_TEST_1", "SRC001", "subj_01", "anon_01", "CONSENTED", "UNKNOWN",
]

SESSIONS_HEADER = [
    "session_id", "participant_id", "dataset_id", "original_session_id",
    "video_filename", "duration_ms", "original_fps", "resolution",
    "lighting_condition", "camera_position", "glasses_condition",
    "occlusion_condition", "activity_type",
]

SESSION_ROW = [
    "SS_TEST_1", "PT_TEST_1", "SRC001", "sess_01", "video1.avi",
    "60000", "30", "640x480", "day", "dash", "no", "none", "driving",
]

EPISODES_HEADER = [
    "episode_id", "session_id", "participant_id", "dataset_id", "start_ms",
    "end_ms", "domain", "behavior_code", "reference_label", "annotator_id",
    "annotation_confidence", "lighting_condition", "occlusion_condition",
    "annotation_notes",
]

WINDOWS_HEADER = [
    "window_id", "session_id", "participant_id", "dataset_id",
    "window_start_ms", "window_end_ms", "domain", "reference_label",
    "annotator_id", "annotation_confidence", "lighting_condition",
    "occlusion_condition", "annotation_notes",
]

ANNOTATORS_HEADER = [
    "annotator_id", "name", "training_status",
    "independent_annotation_enabled", "access_to_engine_scores", "notes",
]

ANNOTATOR_ROW = [
    "ANN_1", "Annotator One", "TRAINED", "YES", "NO", "note",
]

BEHAVIOR_HEADER = [
    "behavior_code", "behavior_name", "domain", "definition",
    "inclusion_criterion", "exclusion_criterion", "annotation_unit",
    "source_label_relation", "human_assessment_required", "status",
]

BEHAVIOR_SLEEP_001 = [
    "SLEEP_001", "Prolonged Eye Closure", "SLEEPINESS", "def", "inc",
    "exc", "episode", "rel", "YES", "PROPOSED",
]

BEHAVIOR_EYE_001 = [
    "EYE_001", "Blink", "FATIGUE", "def", "inc", "exc", "episode",
    "rel", "YES", "PROPOSED",
]


def _write_csv(path: Path, header: list, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)


def _make_valid_project(root: Path) -> Path:
    """Create a minimal project that passes all 14 checks."""
    _write_csv(root / "data" / "catalog" / "datasets.csv",
               DATASETS_HEADER, [DATASET_ROW])
    _write_csv(root / "data" / "catalog" / "compatibility_matrix.csv",
               COMPAT_HEADER, [COMPAT_ROW])
    _write_csv(root / "data" / "catalog" / "licenses.csv",
               LICENSES_HEADER, [LICENSE_ROW])
    _write_csv(root / "data" / "catalog" / "sources_registry.csv",
               SOURCES_HEADER, [])
    _write_csv(root / "documentation" / "behavior_dictionary.csv",
               BEHAVIOR_HEADER, [BEHAVIOR_SLEEP_001, BEHAVIOR_EYE_001])
    _write_csv(root / "data" / "annotation" / "participants.csv",
               PARTICIPANTS_HEADER, [PARTICIPANT_ROW])
    _write_csv(root / "data" / "annotation" / "sessions.csv",
               SESSIONS_HEADER, [SESSION_ROW])
    _write_csv(root / "data" / "annotation" / "episodes.csv",
               EPISODES_HEADER, [])
    _write_csv(root / "data" / "annotation" / "windows.csv",
               WINDOWS_HEADER, [])
    _write_csv(root / "data" / "annotation" / "annotators.csv",
               ANNOTATORS_HEADER, [ANNOTATOR_ROW])
    (root / "data" / "raw" / "TEST").mkdir(parents=True, exist_ok=True)
    return root


def _check_ids(report, check_id, severity="ERROR"):
    return [i for i in report.issues
            if i["check_id"] == check_id and i["severity"] == severity]


@pytest.fixture()
def project(tmp_path):
    return _make_valid_project(tmp_path)


# ---------------------------------------------------------------------------
# Base case
# ---------------------------------------------------------------------------

def test_valid_project_passes(project):
    report = validate_project(project)
    assert report.status == "PASS", [
        (i["check_id"], i["message"]) for i in report.issues
    ]
    assert report.summary["errors"] == 0


# ---------------------------------------------------------------------------
# V01 duplicate identifiers
# ---------------------------------------------------------------------------

def test_v01_duplicate_dataset_id(project):
    _write_csv(project / "data" / "catalog" / "datasets.csv",
               DATASETS_HEADER, [DATASET_ROW, DATASET_ROW])
    report = validate_project(project)
    assert _check_ids(report, "V01")
    assert report.status == "FAIL"


# ---------------------------------------------------------------------------
# V02 dangling references
# ---------------------------------------------------------------------------

def test_v02_compatibility_references_missing_dataset(project):
    bad = list(COMPAT_ROW)
    bad[0] = "SRC999"
    _write_csv(project / "data" / "catalog" / "compatibility_matrix.csv",
               COMPAT_HEADER, [bad])
    report = validate_project(project)
    assert any("SRC999" in i["message"] for i in _check_ids(report, "V02"))


def test_v02_episode_references_missing_session(project):
    row = ["EP_1", "SS_MISSING", "PT_TEST_1", "SRC001", "0", "1000",
           "SLEEPINESS", "SLEEP_001", "PRESENT", "ANN_1", "HIGH",
           "day", "none", "note"]
    _write_csv(project / "data" / "annotation" / "episodes.csv",
               EPISODES_HEADER, [row])
    report = validate_project(project)
    assert any("SS_MISSING" in i["message"]
               for i in _check_ids(report, "V02"))
    # also triggers V14 (no corresponding session)
    assert _check_ids(report, "V14")


# ---------------------------------------------------------------------------
# V03 negative timestamps
# ---------------------------------------------------------------------------

def test_v03_negative_timestamp(project):
    row = ["EP_1", "SS_TEST_1", "PT_TEST_1", "SRC001", "-5", "1000",
           "SLEEPINESS", "SLEEP_001", "PRESENT", "ANN_1", "HIGH",
           "day", "none", "note"]
    _write_csv(project / "data" / "annotation" / "episodes.csv",
               EPISODES_HEADER, [row])
    report = validate_project(project)
    assert _check_ids(report, "V03")


def test_v03_non_integer_timestamp(project):
    row = ["EP_1", "SS_TEST_1", "PT_TEST_1", "SRC001", "abc", "1000",
           "SLEEPINESS", "SLEEP_001", "PRESENT", "ANN_1", "HIGH",
           "day", "none", "note"]
    _write_csv(project / "data" / "annotation" / "episodes.csv",
               EPISODES_HEADER, [row])
    report = validate_project(project)
    assert _check_ids(report, "V03")


# ---------------------------------------------------------------------------
# V04 end before start
# ---------------------------------------------------------------------------

def test_v04_end_before_start(project):
    row = ["EP_1", "SS_TEST_1", "PT_TEST_1", "SRC001", "5000", "1000",
           "SLEEPINESS", "SLEEP_001", "PRESENT", "ANN_1", "HIGH",
           "day", "none", "note"]
    _write_csv(project / "data" / "annotation" / "episodes.csv",
               EPISODES_HEADER, [row])
    report = validate_project(project)
    assert _check_ids(report, "V04")


# ---------------------------------------------------------------------------
# V05 duration incompatible with session
# ---------------------------------------------------------------------------

def test_v05_episode_exceeds_session_duration(project):
    row = ["EP_1", "SS_TEST_1", "PT_TEST_1", "SRC001", "50000", "90000",
           "SLEEPINESS", "SLEEP_001", "PRESENT", "ANN_1", "HIGH",
           "day", "none", "note"]  # session duration_ms = 60000
    _write_csv(project / "data" / "annotation" / "episodes.csv",
               EPISODES_HEADER, [row])
    report = validate_project(project)
    assert _check_ids(report, "V05")


# ---------------------------------------------------------------------------
# V06 invalid domains
# ---------------------------------------------------------------------------

def test_v06_invalid_domain(project):
    row = ["EP_1", "SS_TEST_1", "PT_TEST_1", "SRC001", "0", "1000",
           "INTOXICATION", "SLEEP_001", "PRESENT", "ANN_1", "HIGH",
           "day", "none", "note"]
    _write_csv(project / "data" / "annotation" / "episodes.csv",
               EPISODES_HEADER, [row])
    report = validate_project(project)
    assert any("INTOXICATION" in i["message"]
               for i in _check_ids(report, "V06"))


# ---------------------------------------------------------------------------
# V07 invalid labels
# ---------------------------------------------------------------------------

def test_v07_invalid_reference_label(project):
    row = ["EP_1", "SS_TEST_1", "PT_TEST_1", "SRC001", "0", "1000",
           "SLEEPINESS", "SLEEP_001", "MAYBE", "ANN_1", "HIGH",
           "day", "none", "note"]
    _write_csv(project / "data" / "annotation" / "episodes.csv",
               EPISODES_HEADER, [row])
    report = validate_project(project)
    assert any("MAYBE" in i["message"] for i in _check_ids(report, "V07"))


def test_v07_invalid_access_status(project):
    row = list(DATASET_ROW)
    row[19] = "SUPER_EASY"  # access_status column
    _write_csv(project / "data" / "catalog" / "datasets.csv",
               DATASETS_HEADER, [row])
    report = validate_project(project)
    assert any("SUPER_EASY" in i["message"]
               for i in _check_ids(report, "V07"))


# ---------------------------------------------------------------------------
# V08 missing required metadata
# ---------------------------------------------------------------------------

def test_v08_empty_required_field(project):
    row = list(DATASET_ROW)
    row[1] = ""  # dataset_name empty
    _write_csv(project / "data" / "catalog" / "datasets.csv",
               DATASETS_HEADER, [row])
    report = validate_project(project)
    assert any("dataset_name" in i["message"]
               for i in _check_ids(report, "V08"))


# ---------------------------------------------------------------------------
# V09 files without origin
# ---------------------------------------------------------------------------

def test_v09_unregistered_raw_file(project):
    raw_file = project / "data" / "raw" / "TEST" / "orphan.avi"
    raw_file.write_bytes(b"not registered")
    report = validate_project(project)
    assert any("orphan.avi" in i["file"] or "orphan.avi" in i["message"]
               for i in _check_ids(report, "V09"))


def test_v09_registry_row_without_path(project):
    row = ["SF_1", "SRC001", "file.avi", "", "a" * 64, "avi", "10",
           "2026-11-19", "AVAILABLE", "REGISTERED"]
    _write_csv(project / "data" / "catalog" / "sources_registry.csv",
               SOURCES_HEADER, [row])
    report = validate_project(project)
    assert any("original_path" in i["message"]
               for i in _check_ids(report, "V09"))


def test_v09_gitkeep_sentinel_ignored(project):
    sentinel = project / "data" / "raw" / "TEST" / ".gitkeep"
    sentinel.write_bytes(b"")
    report = validate_project(project)
    assert not any(".gitkeep" in i["file"] or ".gitkeep" in i["message"]
                   for i in _check_ids(report, "V09"))


# ---------------------------------------------------------------------------
# V10 checksum divergence
# ---------------------------------------------------------------------------

def test_v10_checksum_divergent(project):
    target = project / "data" / "raw" / "TEST" / "clip.avi"
    target.write_bytes(b"original content")
    good = hashlib.sha256(b"original content").hexdigest()
    row = ["SF_1", "SRC001", "clip.avi", "data/raw/TEST/clip.avi",
           good, "avi", "16", "2026-11-19", "AVAILABLE", "REGISTERED"]
    _write_csv(project / "data" / "catalog" / "sources_registry.csv",
               SOURCES_HEADER, [row])
    # integrity OK -> no V10
    report = validate_project(project)
    assert not _check_ids(report, "V10")

    # tamper the file -> V10
    target.write_bytes(b"tampered content")
    report = validate_project(project)
    assert _check_ids(report, "V10")


# ---------------------------------------------------------------------------
# V11 participants without origin
# ---------------------------------------------------------------------------

def test_v11_participant_without_origin(project):
    row = ["PT_TEST_2", "SRC001", "", "anon_02", "CONSENTED", "UNKNOWN"]
    _write_csv(project / "data" / "annotation" / "participants.csv",
               PARTICIPANTS_HEADER, [PARTICIPANT_ROW, row])
    report = validate_project(project)
    assert any("PT_TEST_2" in i["record_id"]
               for i in _check_ids(report, "V11"))


# ---------------------------------------------------------------------------
# V12 domain incompatibility
# ---------------------------------------------------------------------------

def test_v12_behavior_domain_mismatch(project):
    row = ["EP_1", "SS_TEST_1", "PT_TEST_1", "SRC001", "0", "1000",
           "FATIGUE", "SLEEP_001", "PRESENT", "ANN_1", "HIGH",
           "day", "none", "note"]  # SLEEP_001 belongs to SLEEPINESS
    _write_csv(project / "data" / "annotation" / "episodes.csv",
               EPISODES_HEADER, [row])
    report = validate_project(project)
    assert any("SLEEP_001" in i["message"] for i in _check_ids(report, "V12"))


# ---------------------------------------------------------------------------
# V13 overlapping windows
# ---------------------------------------------------------------------------

def test_v13_overlapping_windows(project):
    rows = [
        ["WN_1", "SS_TEST_1", "PT_TEST_1", "SRC001", "0", "5000",
         "SLEEPINESS", "PRESENT", "ANN_1", "HIGH", "day", "none", "n"],
        ["WN_2", "SS_TEST_1", "PT_TEST_1", "SRC001", "3000", "8000",
         "SLEEPINESS", "PRESENT", "ANN_1", "HIGH", "day", "none", "n"],
    ]
    _write_csv(project / "data" / "annotation" / "windows.csv",
               WINDOWS_HEADER, rows)
    report = validate_project(project)
    assert _check_ids(report, "V13")


def test_v13_overlapping_same_behavior_episodes(project):
    rows = [
        ["EP_1", "SS_TEST_1", "PT_TEST_1", "SRC001", "0", "5000",
         "SLEEPINESS", "SLEEP_003", "PRESENT", "ANN_1", "HIGH",
         "day", "none", "n"],
        ["EP_2", "SS_TEST_1", "PT_TEST_1", "SRC001", "3000", "8000",
         "SLEEPINESS", "SLEEP_003", "PRESENT", "ANN_1", "HIGH",
         "day", "none", "n"],
    ]
    _write_csv(project / "data" / "annotation" / "episodes.csv",
               EPISODES_HEADER, rows)
    report = validate_project(project)
    assert _check_ids(report, "V13")


def test_v13_different_behavior_overlap_allowed(project):
    rows = [
        ["EP_1", "SS_TEST_1", "PT_TEST_1", "SRC001", "0", "5000",
         "SLEEPINESS", "SLEEP_003", "PRESENT", "ANN_1", "HIGH",
         "day", "none", "n"],
        ["EP_2", "SS_TEST_1", "PT_TEST_1", "SRC001", "3000", "8000",
         "SLEEPINESS", "SLEEP_001", "PRESENT", "ANN_1", "HIGH",
         "day", "none", "n"],
    ]
    _write_csv(project / "data" / "annotation" / "episodes.csv",
               EPISODES_HEADER, rows)
    report = validate_project(project)
    assert not _check_ids(report, "V13")


# ---------------------------------------------------------------------------
# V14 episode without session
# ---------------------------------------------------------------------------

def test_v14_episode_without_session(project):
    row = ["EP_1", "SS_GONE", "PT_TEST_1", "SRC001", "0", "1000",
           "SLEEPINESS", "SLEEP_001", "PRESENT", "ANN_1", "HIGH",
           "day", "none", "note"]
    _write_csv(project / "data" / "annotation" / "episodes.csv",
               EPISODES_HEADER, [row])
    report = validate_project(project)
    assert _check_ids(report, "V14")


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def test_reports_written(project, tmp_path):
    from validate_dataset import write_reports
    report = validate_project(project)
    report_dir = tmp_path / "out_reports"
    json_path, csv_path = write_reports(report, report_dir)
    assert json_path.exists()
    assert csv_path.exists()
    import json
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["status"] == "PASS"
    assert "issues" in data
