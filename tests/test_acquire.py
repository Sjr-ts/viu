"""Tests for the legality gate and registry id helpers in acquire.py.

The gate is the project's door to the outside world: only CLEARED sources
may be fetched. These tests pin its behaviour (protocol §12 criterion 7).
"""

import csv

import acquire


# ---------------------------------------------------------------- gate()

def test_gate_cleared_cc_by():
    status, reason = acquire.gate({
        "dataset_id": "SRC003",
        "license_name": "CC-BY (Creative Commons Attribution)",
        "permission_required": "NO",
        "redistribution_permission": "YES",
    })
    assert status == "CLEARED"
    assert "CC-BY" in reason


def test_gate_blocked_unknown_license():
    status, reason = acquire.gate({
        "license_name": "UNKNOWN", "permission_required": "NO",
    })
    assert status == "BLOCKED"
    assert "UNKNOWN" in reason


def test_gate_blocked_empty_license():
    status, _ = acquire.gate({"license_name": "", "permission_required": ""})
    assert status == "BLOCKED"


def test_gate_blocked_permission_required():
    status, reason = acquire.gate({
        "license_name": "EULA", "permission_required": "YES (signed form)",
    })
    assert status == "BLOCKED"
    assert "permission" in reason.lower()


def test_gate_blocked_review_required():
    status, _ = acquire.gate({
        "license_name": "REVIEW REQUIRED", "permission_required": "NO",
    })
    assert status == "BLOCKED"


def test_gate_cleared_local_when_redistribution_restricted():
    status, _ = acquire.gate({
        "license_name": "CC BY-NC",
        "permission_required": "NO",
        "redistribution_permission": "RESTRICTED",
    })
    assert status == "CLEARED-LOCAL"


def test_gate_missing_license_row():
    status, reason = acquire.gate(None)
    assert status == "BLOCKED"
    assert "licenses.csv" in reason


def test_gate_real_src003_is_cleared():
    lic = acquire.load_licenses()["SRC003"]
    status, _ = acquire.gate(lic)
    assert status == "CLEARED"


def test_gate_real_blocked_sources_stay_blocked():
    lic_map = acquire.load_licenses()
    for sid in ("SRC001", "SRC002", "SRC004", "SRC005",
                "SRC006", "SRC007", "SRC008"):
        status, _ = acquire.gate(lic_map.get(sid))
        assert status == "BLOCKED", f"{sid} must not be fetchable"


# ------------------------------------------------------- next_source_id()

def test_next_source_id_starts_at_sf001(tmp_path, monkeypatch):
    monkeypatch.setattr(acquire, "REGISTRY", tmp_path / "registry.csv")
    assert acquire.next_source_id() == "SF001"


def test_next_source_id_appends_after_existing(tmp_path, monkeypatch):
    reg = tmp_path / "registry.csv"
    monkeypatch.setattr(acquire, "REGISTRY", reg)
    with reg.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["source_file_id", "dataset_id"])
        w.writerow(["SF001", "SRC003"])
        w.writerow(["SF007", "SRC003"])
    assert acquire.next_source_id() == "SF008"


def test_registered_paths_reads_only_nonempty_paths(tmp_path, monkeypatch):
    reg = tmp_path / "registry.csv"
    monkeypatch.setattr(acquire, "REGISTRY", reg)
    with reg.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["source_file_id", "dataset_id", "original_path"])
        w.writerow(["SF001", "SRC003", "data/raw/YawDD/user06.tar"])
        w.writerow(["SF002", "SRC003", ""])
    assert acquire.registered_paths() == {"data/raw/YawDD/user06.tar"}
