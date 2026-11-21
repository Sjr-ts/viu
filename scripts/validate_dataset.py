#!/usr/bin/env python3
"""NightEyes dataset validation module.

Validates the Part 1 catalog/annotation structure against the 14 checks
defined in the NightEyes implementation plan (section 10). Never fixes
data silently: all problems are reported as issues.

Checks:
    V01 duplicate identifiers
    V02 non-existent references between files
    V03 negative / unparseable timestamps
    V04 end time smaller than start time
    V05 duration incompatible with the session
    V06 invalid domains
    V07 invalid labels (enums)
    V08 missing required metadata
    V09 files without identified origin
    V10 files with divergent checksum
    V11 participants without origin identification
    V12 annotations whose classification is incompatible with the domain
    V13 improperly overlapping temporal windows
    V14 episodes without corresponding session

Usage:
    python scripts/validate_dataset.py [--root PROJECT_ROOT]
                                       [--report-dir REPORT_DIR]

Reports:
    <report-dir>/validation_report.json
    <report-dir>/validation_report.csv

Exit code: 0 = no errors (warnings allowed), 1 = errors found.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

# ---------------------------------------------------------------------------
# Controlled vocabularies (must mirror documentation/metadata_dictionary.csv)
# ---------------------------------------------------------------------------

NIGHTEYES_STATES = ("PRESENT", "ABSENT", "UNCERTAIN", "UNOBSERVABLE")
DOMAINS = ("FATIGUE", "SLEEPINESS", "DISTRACTION", "QUALITY")
PRIMARY_DOMAINS = ("FATIGUE", "SLEEPINESS", "DISTRACTION", "MULTI_DOMAIN")
COMPATIBILITY_LEVELS = (
    "DIRECT", "PARTIAL", "COMPLEMENTARY", "INCOMPATIBLE", "UNVERIFIED",
)
ACCESS_STATUSES = (
    "AVAILABLE", "REQUIRES_PERMISSION", "REVIEW_REQUIRED", "RESTRICTED",
    "UNKNOWN",
)
YES_NO = ("YES", "NO")
PROCESSING_STATUSES = (
    "REGISTERED", "VERIFIED", "TRANSFORMED", "QUARANTINED",
)

REQUIRED_DATASETS_FIELDS = (
    "dataset_id", "dataset_name", "primary_domain", "institution",
    "access_status", "verification_date", "license",
)
REQUIRED_COMPAT_FIELDS = (
    "dataset_id", "source_label", "source_label_definition", "mapped_domain",
    "mapped_behavior", "compatibility_level", "mapping_method",
    "temporal_resolution", "requires_reannotation",
)
REQUIRED_LICENSE_FIELDS = (
    "dataset_id", "license_name", "commercial_usage",
    "redistribution_permission", "permission_required", "verification_date",
)
REQUIRED_SOURCE_FIELDS = (
    "source_file_id", "dataset_id", "original_filename", "original_path",
    "checksum_sha256", "file_type", "file_size", "import_date",
    "access_permission", "processing_status",
)
REQUIRED_PARTICIPANT_FIELDS = (
    "participant_id", "dataset_id", "original_participant_id",
    "consent_status",
)
REQUIRED_SESSION_FIELDS = (
    "session_id", "participant_id", "dataset_id", "video_filename",
)
REQUIRED_EPISODE_FIELDS = (
    "episode_id", "session_id", "participant_id", "dataset_id", "start_ms",
    "end_ms", "domain", "reference_label", "annotator_id",
)
REQUIRED_WINDOW_FIELDS = (
    "window_id", "session_id", "participant_id", "dataset_id",
    "window_start_ms", "window_end_ms", "domain", "reference_label",
    "annotator_id",
)

SHA256_HEX_LEN = 64


@dataclass
class Issue:
    check_id: str
    severity: str  # ERROR | WARNING
    file: str
    record_id: str
    message: str


@dataclass
class ValidationReport:
    report_version: str = "1.0"
    generated_at: str = ""
    project_root: str = ""
    status: str = "PASS"
    summary: dict = field(default_factory=dict)
    issues: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------------

def _read_csv(path: Path) -> Optional[pd.DataFrame]:
    """Read a CSV as strings. Returns None if the file does not exist."""
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
    except Exception as exc:  # malformed CSV is itself a finding
        raise ValueError(f"Cannot parse CSV {path}: {exc}") from exc
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _blank(value) -> bool:
    return value is None or str(value).strip() == ""


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _to_int(value) -> Optional[int]:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _behavior_domain_map(root: Path) -> dict:
    """Load behavior_code -> domain from the behavior dictionary."""
    df = _read_csv(root / "documentation" / "behavior_dictionary.csv")
    if df is None or "behavior_code" not in df.columns:
        return {}
    domain_col = "domain" if "domain" in df.columns else None
    mapping = {}
    if domain_col:
        for _, row in df.iterrows():
            mapping[str(row["behavior_code"]).strip()] = \
                str(row[domain_col]).strip()
    return mapping


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def _check_v01_duplicates(files: dict, issues: list) -> None:
    """V01: duplicate identifiers."""
    unique_keys = {
        "datasets.csv": ("dataset_id", "datasets.csv"),
        "licenses.csv": ("dataset_id", "licenses.csv"),
        "sources_registry.csv": ("source_file_id", "sources_registry.csv"),
        "participants.csv": ("participant_id", "participants.csv"),
        "sessions.csv": ("session_id", "sessions.csv"),
        "episodes.csv": ("episode_id", "episodes.csv"),
        "windows.csv": ("window_id", "windows.csv"),
        "annotators.csv": ("annotator_id", "annotators.csv"),
        "behavior_dictionary.csv": ("behavior_code", "behavior_dictionary.csv"),
    }
    for fname, (key, label) in unique_keys.items():
        df = files.get(fname)
        if df is None or key not in df.columns or df.empty:
            continue
        duplicated = df[df.duplicated(subset=[key], keep=False)]
        for _, row in duplicated.iterrows():
            issues.append(Issue(
                "V01", "ERROR", label, str(row[key]).strip(),
                f"Duplicate identifier '{key}' = '{row[key]}'",
            ))

    # participants: (dataset_id, original_participant_id) must be unique
    df = files.get("participants.csv")
    if df is not None and not df.empty:
        cols = {"dataset_id", "original_participant_id"}
        if cols.issubset(df.columns):
            dup = df[df.duplicated(subset=sorted(cols), keep=False)]
            for _, row in dup.iterrows():
                issues.append(Issue(
                    "V01", "ERROR", "participants.csv",
                    str(row["participant_id"]),
                    "Duplicate (dataset_id, original_participant_id) = "
                    f"({row['dataset_id']}, {row['original_participant_id']})",
                ))

    # compatibility: mapping rows must be unique
    df = files.get("compatibility_matrix.csv")
    if df is not None and not df.empty:
        cols = ["dataset_id", "source_label", "mapped_domain",
                "mapped_behavior"]
        if all(c in df.columns for c in cols):
            dup = df[df.duplicated(subset=cols, keep=False)]
            for _, row in dup.iterrows():
                issues.append(Issue(
                    "V01", "ERROR", "compatibility_matrix.csv",
                    str(row["dataset_id"]),
                    "Duplicate mapping row for "
                    f"{row['dataset_id']} / {row['source_label']} / "
                    f"{row['mapped_domain']} / {row['mapped_behavior']}",
                ))


def _check_v02_references(files: dict, issues: list) -> None:
    """V02: references that do not exist between files."""
    datasets = _id_set(files, "datasets.csv", "dataset_id")
    participants = _id_set(files, "participants.csv", "participant_id")
    sessions = _id_set(files, "sessions.csv", "session_id")
    annotators = _id_set(files, "annotators.csv", "annotator_id")
    behaviors = set(_behavior_domain_map_from_df(
        files.get("behavior_dictionary.csv")))

    def ref(fname, col, targets, target_name, id_col=None):
        df = files.get(fname)
        if df is None or df.empty or col not in df.columns:
            return
        idc = id_col or (df.columns[0])
        for _, row in df.iterrows():
            value = str(row[col]).strip()
            if _blank(value):
                continue
            if value not in targets:
                issues.append(Issue(
                    "V02", "ERROR", fname, str(row[idc]).strip(),
                    f"Reference '{col}' = '{value}' does not exist in "
                    f"{target_name}",
                ))

    ref("compatibility_matrix.csv", "dataset_id", datasets, "datasets.csv")
    ref("licenses.csv", "dataset_id", datasets, "datasets.csv")
    ref("sources_registry.csv", "dataset_id", datasets, "datasets.csv")
    ref("participants.csv", "dataset_id", datasets, "datasets.csv")
    ref("sessions.csv", "dataset_id", datasets, "datasets.csv")
    ref("sessions.csv", "participant_id", participants, "participants.csv")
    ref("episodes.csv", "dataset_id", datasets, "datasets.csv")
    ref("episodes.csv", "session_id", sessions, "sessions.csv")
    ref("episodes.csv", "participant_id", participants, "participants.csv")
    ref("windows.csv", "dataset_id", datasets, "datasets.csv")
    ref("windows.csv", "session_id", sessions, "sessions.csv")
    ref("windows.csv", "participant_id", participants, "participants.csv")

    # annotator references (only when the annotators registry has entries)
    if annotators:
        ref("episodes.csv", "annotator_id", annotators, "annotators.csv")
        ref("windows.csv", "annotator_id", annotators, "annotators.csv")

    # behavior code references
    if behaviors:
        for fname in ("episodes.csv", "windows.csv"):
            df = files.get(fname)
            if df is None or df.empty or "behavior_code" not in df.columns:
                continue
            idc = df.columns[0]
            for _, row in df.iterrows():
                value = str(row.get("behavior_code", "")).strip()
                if _blank(value):
                    continue
                if value not in behaviors:
                    issues.append(Issue(
                        "V02", "ERROR", fname, str(row[idc]).strip(),
                        f"behavior_code '{value}' does not exist in "
                        "behavior_dictionary.csv",
                    ))


def _id_set(files: dict, fname: str, key: str) -> set:
    df = files.get(fname)
    if df is None or key not in df.columns:
        return set()
    return {str(v).strip() for v in df[key] if not _blank(v)}


def _behavior_domain_map_from_df(df) -> dict:
    if df is None or "behavior_code" not in df.columns \
            or "domain" not in df.columns:
        return {}
    return {str(r["behavior_code"]).strip(): str(r["domain"]).strip()
            for _, r in df.iterrows()}


def _check_v03_timestamps(files: dict, issues: list) -> None:
    """V03: negative or unparseable timestamps."""
    specs = (
        ("episodes.csv", ("start_ms", "end_ms"), "episode_id"),
        ("windows.csv", ("window_start_ms", "window_end_ms"), "window_id"),
    )
    for fname, cols, idcol in specs:
        df = files.get(fname)
        if df is None or df.empty:
            continue
        for col in cols:
            if col not in df.columns:
                continue
            for _, row in df.iterrows():
                raw = str(row[col]).strip()
                if _blank(raw):
                    continue
                value = _to_int(raw)
                if value is None:
                    issues.append(Issue(
                        "V03", "ERROR", fname, str(row[idcol]).strip(),
                        f"Timestamp '{col}' is not an integer: '{raw}'",
                    ))
                elif value < 0:
                    issues.append(Issue(
                        "V03", "ERROR", fname, str(row[idcol]).strip(),
                        f"Negative timestamp: {col} = {value}",
                    ))


def _check_v04_order(files: dict, issues: list) -> None:
    """V04: end time smaller than (or equal to) start time."""
    specs = (
        ("episodes.csv", "start_ms", "end_ms", "episode_id"),
        ("windows.csv", "window_start_ms", "window_end_ms", "window_id"),
    )
    for fname, start_col, end_col, idcol in specs:
        df = files.get(fname)
        if df is None or df.empty:
            continue
        if start_col not in df.columns or end_col not in df.columns:
            continue
        for _, row in df.iterrows():
            start = _to_int(row[start_col])
            end = _to_int(row[end_col])
            if start is None or end is None:
                continue
            if end <= start:
                issues.append(Issue(
                    "V04", "ERROR", fname, str(row[idcol]).strip(),
                    f"end ({end}) must be greater than start ({start})",
                ))


def _check_v05_duration(files: dict, issues: list) -> None:
    """V05: episode/window duration incompatible with the session."""
    sessions = files.get("sessions.csv")
    if sessions is None or sessions.empty \
            or "duration_ms" not in sessions.columns:
        return
    dur_by_session = {}
    for _, row in sessions.iterrows():
        dur = _to_int(row.get("duration_ms", ""))
        if dur is not None and dur > 0:
            dur_by_session[str(row["session_id"]).strip()] = dur

    specs = (
        ("episodes.csv", "start_ms", "end_ms", "episode_id"),
        ("windows.csv", "window_start_ms", "window_end_ms", "window_id"),
    )
    for fname, start_col, end_col, idcol in specs:
        df = files.get(fname)
        if df is None or df.empty or "session_id" not in df.columns:
            continue
        for _, row in df.iterrows():
            sid = str(row["session_id"]).strip()
            if sid not in dur_by_session:
                continue
            end = _to_int(row.get(end_col, ""))
            if end is None:
                continue
            if end > dur_by_session[sid]:
                issues.append(Issue(
                    "V05", "ERROR", fname, str(row[idcol]).strip(),
                    f"end ({end} ms) exceeds session '{sid}' duration "
                    f"({dur_by_session[sid]} ms)",
                ))


def _check_v06_domains(files: dict, issues: list) -> None:
    """V06: invalid domains."""
    checks = (
        ("episodes.csv", "domain", "episode_id"),
        ("windows.csv", "domain", "window_id"),
        ("compatibility_matrix.csv", "mapped_domain", "dataset_id"),
    )
    for fname, col, idcol in checks:
        df = files.get(fname)
        if df is None or df.empty or col not in df.columns:
            continue
        for _, row in df.iterrows():
            value = str(row[col]).strip()
            if _blank(value):
                continue
            if value not in DOMAINS:
                issues.append(Issue(
                    "V06", "ERROR", fname, str(row[idcol]).strip(),
                    f"Invalid domain '{value}' (allowed: "
                    f"{', '.join(DOMAINS)})",
                ))

    df = files.get("datasets.csv")
    if df is not None and not df.empty and "primary_domain" in df.columns:
        for _, row in df.iterrows():
            value = str(row["primary_domain"]).strip()
            if not _blank(value) and value not in PRIMARY_DOMAINS:
                issues.append(Issue(
                    "V06", "ERROR", "datasets.csv",
                    str(row["dataset_id"]).strip(),
                    f"Invalid primary_domain '{value}' (allowed: "
                    f"{', '.join(PRIMARY_DOMAINS)})",
                ))


def _check_v07_labels(files: dict, issues: list) -> None:
    """V07: invalid labels (enums)."""
    enum_specs = (
        ("episodes.csv", "reference_label", "episode_id", NIGHTEYES_STATES),
        ("windows.csv", "reference_label", "window_id", NIGHTEYES_STATES),
        ("compatibility_matrix.csv", "compatibility_level", "dataset_id",
         COMPATIBILITY_LEVELS),
        ("compatibility_matrix.csv", "requires_reannotation", "dataset_id",
         YES_NO),
        ("datasets.csv", "access_status", "dataset_id", ACCESS_STATUSES),
        ("sources_registry.csv", "processing_status", "source_file_id",
         PROCESSING_STATUSES),
    )
    for fname, col, idcol, allowed in enum_specs:
        df = files.get(fname)
        if df is None or df.empty or col not in df.columns:
            continue
        for _, row in df.iterrows():
            value = str(row[col]).strip()
            if _blank(value):
                continue
            if value not in allowed:
                issues.append(Issue(
                    "V07", "ERROR", fname, str(row[idcol]).strip(),
                    f"Invalid {col} '{value}' (allowed: {', '.join(allowed)})",
                ))


def _check_v08_required(files: dict, issues: list) -> None:
    """V08: missing required metadata."""
    specs = (
        ("datasets.csv", REQUIRED_DATASETS_FIELDS, "dataset_id"),
        ("compatibility_matrix.csv", REQUIRED_COMPAT_FIELDS, "dataset_id"),
        ("licenses.csv", REQUIRED_LICENSE_FIELDS, "dataset_id"),
        ("sources_registry.csv", REQUIRED_SOURCE_FIELDS, "source_file_id"),
        ("participants.csv", REQUIRED_PARTICIPANT_FIELDS, "participant_id"),
        ("sessions.csv", REQUIRED_SESSION_FIELDS, "session_id"),
        ("episodes.csv", REQUIRED_EPISODE_FIELDS, "episode_id"),
        ("windows.csv", REQUIRED_WINDOW_FIELDS, "window_id"),
    )
    for fname, required, idcol in specs:
        df = files.get(fname)
        if df is None or df.empty:
            continue
        for fieldname in required:
            if fieldname not in df.columns:
                issues.append(Issue(
                    "V08", "ERROR", fname, "-",
                    f"Required column '{fieldname}' is missing",
                ))
                continue
            for _, row in df.iterrows():
                if _blank(row[fieldname]):
                    issues.append(Issue(
                        "V08", "ERROR", fname,
                        str(row.get(idcol, "-")).strip() or "-",
                        f"Required field '{fieldname}' is empty",
                    ))


def _check_v09_origin(root: Path, files: dict, issues: list) -> None:
    """V09: files without identified origin / registry inconsistencies."""
    registry = files.get("sources_registry.csv")
    registered_paths = set()

    if registry is not None and not registry.empty:
        for _, row in registry.iterrows():
            rid = str(row.get("source_file_id", "-")).strip() or "-"
            path_value = str(row.get("original_path", "")).strip()
            if _blank(path_value):
                issues.append(Issue(
                    "V09", "ERROR", "sources_registry.csv", rid,
                    "Registered file has no original_path (origin unknown)",
                ))
                continue
            registered_paths.add(Path(path_value).as_posix())
            abs_path = root / path_value
            if not abs_path.exists():
                issues.append(Issue(
                    "V09", "WARNING", "sources_registry.csv", rid,
                    f"Registered file not found on disk: {path_value}",
                ))

    # Raw files present on disk but not registered
    raw_dir = root / "data" / "raw"
    if raw_dir.exists():
        for path in sorted(raw_dir.rglob("*")):
            if not path.is_file():
                continue
            if path.name.startswith("."):
                continue  # sentinel/placeholder files (.gitkeep) are not data
            rel = path.relative_to(root).as_posix()
            if rel not in registered_paths:
                issues.append(Issue(
                    "V09", "ERROR", rel, path.name,
                    "File present under data/raw/ is not registered in "
                    "sources_registry.csv (origin not identified)",
                ))


def _check_v10_checksum(files: dict, root: Path, issues: list) -> None:
    """V10: files with divergent checksum."""
    registry = files.get("sources_registry.csv")
    if registry is None or registry.empty:
        return
    if "checksum_sha256" not in registry.columns \
            or "original_path" not in registry.columns:
        return
    for _, row in registry.iterrows():
        rid = str(row.get("source_file_id", "-")).strip() or "-"
        expected = str(row.get("checksum_sha256", "")).strip().lower()
        path_value = str(row.get("original_path", "")).strip()
        if _blank(expected) or _blank(path_value):
            continue
        abs_path = root / path_value
        if not abs_path.exists():
            continue  # handled by V09 warning
        actual = _sha256(abs_path)
        if actual != expected:
            issues.append(Issue(
                "V10", "ERROR", "sources_registry.csv", rid,
                f"Checksum divergent for '{path_value}': registry="
                f"{expected} actual={actual}",
            ))


def _check_v11_participants(files: dict, issues: list) -> None:
    """V11: participants without origin identification."""
    df = files.get("participants.csv")
    if df is None or df.empty:
        return
    for _, row in df.iterrows():
        pid = str(row.get("participant_id", "-")).strip() or "-"
        dataset_id = str(row.get("dataset_id", "")).strip()
        original_id = str(row.get("original_participant_id", "")).strip()
        problems = []
        if _blank(dataset_id):
            problems.append("dataset_id empty")
        if _blank(original_id):
            problems.append("original_participant_id empty")
        elif original_id.upper() == "UNKNOWN":
            problems.append("original_participant_id is UNKNOWN")
        if problems:
            issues.append(Issue(
                "V11", "ERROR", "participants.csv", pid,
                "Participant without origin identification: "
                + "; ".join(problems),
            ))


def _check_v12_domain_compatibility(files: dict, behavior_map: dict,
                                    issues: list) -> None:
    """V12: annotation classification incompatible with its domain."""
    if not behavior_map:
        return
    for fname, idcol in (("episodes.csv", "episode_id"),
                         ("windows.csv", "window_id")):
        df = files.get(fname)
        if df is None or df.empty:
            continue
        if "domain" not in df.columns or "behavior_code" not in df.columns:
            continue
        for _, row in df.iterrows():
            code = str(row.get("behavior_code", "")).strip()
            domain = str(row.get("domain", "")).strip()
            if _blank(code) or _blank(domain):
                continue
            expected = behavior_map.get(code)
            if expected is None:
                continue  # reported by V02
            if expected != domain:
                issues.append(Issue(
                    "V12", "ERROR", fname, str(row[idcol]).strip(),
                    f"behavior_code '{code}' belongs to domain "
                    f"'{expected}' but annotation domain is '{domain}'",
                ))


def _check_v13_overlaps(files: dict, issues: list) -> None:
    """V13: improperly overlapping temporal windows."""
    # Episodes: overlap only improper within same session+domain+behavior
    df = files.get("episodes.csv")
    if df is not None and not df.empty:
        needed = {"session_id", "domain", "start_ms", "end_ms",
                  "episode_id"}
        if needed.issubset(df.columns):
            work = df.copy()
            work["_start"] = work["start_ms"].map(_to_int)
            work["_end"] = work["end_ms"].map(_to_int)
            work["_behavior"] = (
                work["behavior_code"].astype(str).str.strip()
                if "behavior_code" in work.columns else ""
            )
            work = work.dropna(subset=["_start", "_end"])
            for keys, group in work.groupby(
                    ["session_id", "domain", "_behavior"], sort=False
            ):
                group = group.sort_values("_start")
                prev_end = None
                prev_id = None
                for _, row in group.iterrows():
                    if prev_end is not None and row["_start"] < prev_end:
                        issues.append(Issue(
                            "V13", "ERROR", "episodes.csv",
                            str(row["episode_id"]).strip(),
                            f"Episode overlaps previous episode '{prev_id}' "
                            f"(session={keys[0]}, domain={keys[1]}, "
                            f"behavior={keys[2] or 'NONE'})",
                        ))
                    if prev_end is None or row["_end"] > prev_end:
                        prev_end = row["_end"]
                        prev_id = str(row["episode_id"]).strip()

    # Windows: must not overlap within the same session+domain
    df = files.get("windows.csv")
    if df is not None and not df.empty:
        needed = {"session_id", "domain", "window_start_ms",
                  "window_end_ms", "window_id"}
        if needed.issubset(df.columns):
            work = df.copy()
            work["_start"] = work["window_start_ms"].map(_to_int)
            work["_end"] = work["window_end_ms"].map(_to_int)
            work = work.dropna(subset=["_start", "_end"])
            for keys, group in work.groupby(["session_id", "domain"],
                                            sort=False):
                group = group.sort_values("_start")
                prev_end = None
                prev_id = None
                for _, row in group.iterrows():
                    if prev_end is not None and row["_start"] < prev_end:
                        issues.append(Issue(
                            "V13", "ERROR", "windows.csv",
                            str(row["window_id"]).strip(),
                            f"Window overlaps previous window '{prev_id}' "
                            f"(session={keys[0]}, domain={keys[1]})",
                        ))
                    if prev_end is None or row["_end"] > prev_end:
                        prev_end = row["_end"]
                        prev_id = str(row["window_id"]).strip()


def _check_v14_sessions(files: dict, issues: list) -> None:
    """V14: episodes without corresponding session."""
    sessions = _id_set(files, "sessions.csv", "session_id")
    if not sessions:
        # sessions registry empty: flag episodes only if they exist
        pass
    for fname, idcol in (("episodes.csv", "episode_id"),
                         ("windows.csv", "window_id")):
        df = files.get(fname)
        if df is None or df.empty or "session_id" not in df.columns:
            continue
        for _, row in df.iterrows():
            sid = str(row["session_id"]).strip()
            if _blank(sid):
                issues.append(Issue(
                    "V14", "ERROR", fname, str(row[idcol]).strip(),
                    "Record has empty session_id (no corresponding session)",
                ))
            elif sid not in sessions:
                issues.append(Issue(
                    "V14", "ERROR", fname, str(row[idcol]).strip(),
                    f"session_id '{sid}' has no corresponding session in "
                    "sessions.csv",
                ))


# ---------------------------------------------------------------------------
# V15–V22 — protocol V0.1 integrity checks (ground truth quality & §8/§12)
# ---------------------------------------------------------------------------

def _check_v15_auto_derived(root: Path, issues: list) -> None:
    df = _read_csv(root / "data" / "annotation" / "episodes.csv")
    if df is None or "annotation_notes" not in df.columns:
        return
    bad = df[df["annotation_notes"].str.contains(
        r"auto-derived|from filename|low confidence draft", case=False, regex=True
    )]
    for _, row in bad.iterrows():
        issues.append(Issue(
            "V15", "ERROR", "episodes.csv", str(row.get("episode_id", "-")),
            "episode label derived from filename/metadata, not human observation",
        ))


def _check_v16_domain_coverage(root: Path, issues: list) -> None:
    df = _read_csv(root / "data" / "annotation" / "episodes.csv")
    if df is None or df.empty or "domain" not in df.columns:
        return
    for domain in ("FATIGUE", "SLEEPINESS", "DISTRACTION"):
        subset = df[df["domain"] == domain]
        if subset.empty:
            issues.append(Issue(
                "V16", "WARNING", "episodes.csv", domain,
                "no annotated episode for protocol domain; coverage incomplete",
            ))
        elif not subset["reference_label"].isin(["PRESENT", "UNCERTAIN"]).any():
            issues.append(Issue(
                "V16", "WARNING", "episodes.csv", domain,
                "no PRESENT/UNCERTAIN observation; domain cannot be evaluated",
            ))


def _check_v17_dual_annotation(root: Path, issues: list) -> None:
    ann = root / "data" / "annotation"
    eps = _read_csv(ann / "episodes.csv")
    if eps is None or eps.empty or "annotator_id" not in eps.columns:
        return
    ids = set(eps["annotator_id"].astype(str).str.strip())
    if "AN_CONSOLIDATED" in ids and "ANN_2" not in ids:
        issues.append(Issue(
            "V17", "WARNING", "episodes.csv", "AN_CONSOLIDATED",
            "consolidated labels exist but no second independent annotator rows",
        ))


def _check_v18_frame_annotations(root: Path, files: dict, issues: list) -> None:
    frames = _read_csv(root / "data" / "annotation" / "frame_annotations.csv")
    if frames is None or frames.empty:
        return
    valid_labels = set(NIGHTEYES_STATES)
    valid_domains = set(PROTOCOL_DOMAINS) if "PROTOCOL_DOMAINS" in globals() else {
        "FATIGUE", "SLEEPINESS", "DISTRACTION",
    }
    sessions = files.get("sessions.csv")
    participants = files.get("participants.csv")
    session_ids = set(sessions["session_id"].astype(str).str.strip()) if sessions is not None else set()
    participant_ids = set(participants["participant_id"].astype(str).str.strip()) if participants is not None else set()
    for _, row in frames.iterrows():
        rid = str(row.get("frame_id", "-"))
        if str(row.get("reference_label", "")).strip() not in valid_labels:
            issues.append(Issue("V18", "ERROR", "frame_annotations.csv", rid, "invalid reference_label"))
        if str(row.get("domain", "")).strip() not in valid_domains:
            issues.append(Issue("V18", "ERROR", "frame_annotations.csv", rid, "invalid domain"))
        if session_ids and str(row.get("session_id", "")).strip() not in session_ids:
            issues.append(Issue("V18", "ERROR", "frame_annotations.csv", rid, "dangling session_id"))
        if participant_ids and str(row.get("participant_id", "")).strip() not in participant_ids:
            issues.append(Issue("V18", "ERROR", "frame_annotations.csv", rid, "dangling participant_id"))
        face = str(row.get("face_visible", "") or "").strip()
        if face and face not in {"YES", "NO", "PARTIAL", "UNKNOWN"}:
            issues.append(Issue("V18", "ERROR", "frame_annotations.csv", rid, "invalid face_visible"))


def _check_v19_default_metadata(root: Path, issues: list) -> None:
    eps = _read_csv(root / "data" / "annotation" / "episodes.csv")
    if eps is None or eps.empty:
        return
    for col in ("lighting_condition", "occlusion_condition"):
        if col not in eps.columns:
            continue
        n = int(eps[col].astype(str).str.strip().eq("UNKNOWN").sum())
        if n:
            issues.append(Issue(
                "V19", "WARNING", "episodes.csv", col,
                f"{n} episode(s) have UNKNOWN {col}; capture conditions incomplete (§9)",
            ))


def _check_v20_consent(root: Path, files: dict, issues: list) -> None:
    parts = files.get("participants.csv")
    eps = _read_csv(root / "data" / "annotation" / "episodes.csv")
    if parts is None or eps is None or eps.empty:
        return
    restricted = set(parts.loc[parts["consent_status"].astype(str).str.strip() == "RESTRICTED",
                               "participant_id"].astype(str).str.strip())
    used = set(eps["participant_id"].astype(str).str.strip()) & restricted
    if used:
        issues.append(Issue(
            "V20", "WARNING", "episodes.csv", "consent",
            f"{len(used)} participant(s) with RESTRICTED consent appear in episodes (§12.7)",
        ))


def _check_v21_splits(root: Path, issues: list) -> None:
    processed = root / "data" / "processed"
    paths = [processed / f"{s}.csv" for s in ("train", "validation", "test")]
    if not any(p.exists() for p in paths):
        issues.append(Issue(
            "V21", "WARNING", "data/processed", "splits",
            "TRAIN/VALIDATION/TEST split not generated (protocol §8)",
        ))
        return
    seen: dict[str, str] = {}
    for path in paths:
        if not path.exists():
            issues.append(Issue("V21", "ERROR", "data/processed", path.name, "missing split file"))
            continue
        df = _read_csv(path)
        if df is None or "participant_id" not in df.columns:
            continue
        for pid in df["participant_id"].astype(str).str.strip():
            if pid in seen and seen[pid] != path.name:
                issues.append(Issue(
                    "V21", "ERROR", "data/processed", pid,
                    f"participant appears in both {seen[pid]} and {path.name}",
                ))
            seen[pid] = path.name


def _check_v22_self_report(root: Path, issues: list) -> None:
    path = root / "data" / "annotation" / "self_reports.csv"
    if not path.exists():
        issues.append(Issue(
            "V22", "WARNING", "self_reports.csv", "KSS",
            "self-report schema absent; KSS cannot be stored separately (§2.2)",
        ))


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def validate_project(root: Path) -> ValidationReport:
    """Run all 14 checks against the project rooted at ``root``."""
    root = Path(root)
    issues: list[Issue] = []

    catalog = root / "data" / "catalog"
    annotation = root / "data" / "annotation"

    paths = {
        "datasets.csv": catalog / "datasets.csv",
        "compatibility_matrix.csv": catalog / "compatibility_matrix.csv",
        "licenses.csv": catalog / "licenses.csv",
        "sources_registry.csv": catalog / "sources_registry.csv",
        "participants.csv": annotation / "participants.csv",
        "sessions.csv": annotation / "sessions.csv",
        "episodes.csv": annotation / "episodes.csv",
        "windows.csv": annotation / "windows.csv",
        "annotators.csv": annotation / "annotators.csv",
        "behavior_dictionary.csv":
            root / "documentation" / "behavior_dictionary.csv",
    }

    files: dict = {}
    for name, path in paths.items():
        try:
            files[name] = _read_csv(path)
        except ValueError as exc:
            issues.append(Issue(
                "V08", "ERROR", name, "-", str(exc),
            ))
            files[name] = None

    behavior_map = _behavior_domain_map(root)

    _check_v01_duplicates(files, issues)
    _check_v02_references(files, issues)
    _check_v03_timestamps(files, issues)
    _check_v04_order(files, issues)
    _check_v05_duration(files, issues)
    _check_v06_domains(files, issues)
    _check_v07_labels(files, issues)
    _check_v08_required(files, issues)
    _check_v09_origin(root, files, issues)
    _check_v10_checksum(files, root, issues)
    _check_v11_participants(files, issues)
    _check_v12_domain_compatibility(files, behavior_map, issues)
    _check_v13_overlaps(files, issues)
    _check_v14_sessions(files, issues)
    _check_v15_auto_derived(root, issues)
    _check_v16_domain_coverage(root, issues)
    _check_v17_dual_annotation(root, issues)
    _check_v18_frame_annotations(root, files, issues)
    _check_v19_default_metadata(root, issues)
    _check_v20_consent(root, files, issues)
    _check_v21_splits(root, issues)
    _check_v22_self_report(root, issues)

    errors = [i for i in issues if i.severity == "ERROR"]
    warnings = [i for i in issues if i.severity == "WARNING"]

    check_ids = [f"V{n:02d}" for n in range(1, 23)]
    per_check = {}
    for cid in check_ids:
        per_check[cid] = {
            "errors": sum(1 for i in issues
                          if i.check_id == cid and i.severity == "ERROR"),
            "warnings": sum(1 for i in issues
                            if i.check_id == cid and i.severity == "WARNING"),
        }

    report = ValidationReport(
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        project_root=str(root),
        status="FAIL" if errors else "PASS",
        summary={
            "errors": len(errors),
            "warnings": len(warnings),
            "checks": per_check,
        },
        issues=[asdict(i) for i in issues],
    )
    return report


def write_reports(report: ValidationReport, report_dir: Path) -> tuple:
    """Write JSON and CSV reports. Returns (json_path, csv_path)."""
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    json_path = report_dir / "validation_report.json"
    csv_path = report_dir / "validation_report.csv"

    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(asdict(report), fh, ensure_ascii=False, indent=2)

    rows = report.issues
    pd.DataFrame(rows, columns=["check_id", "severity", "file", "record_id",
                                "message"]).to_csv(
        csv_path, index=False, encoding="utf-8",
    )
    return json_path, csv_path


def print_issues(report: ValidationReport) -> None:
    """Print a clear human-readable summary of issues."""
    print(f"NightEyes validation - status: {report.status}")
    print(f"  errors:   {report.summary.get('errors', 0)}")
    print(f"  warnings: {report.summary.get('warnings', 0)}")
    if not report.issues:
        print("  no issues found")
        return
    print("-" * 72)
    for issue in report.issues:
        print(f"[{issue['severity']}] {issue['check_id']} "
              f"{issue['file']} #{issue['record_id']}: {issue['message']}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the NightEyes dataset structure (Part 1).",
    )
    default_root = Path(__file__).resolve().parent.parent
    parser.add_argument(
        "--root", type=Path, default=default_root,
        help="Project root (default: repository root)",
    )
    parser.add_argument(
        "--report-dir", type=Path, default=None,
        help="Directory for reports (default: <root>/data/reports)",
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    report_dir = (args.report_dir or (root / "data" / "reports")).resolve()

    try:
        report = validate_project(root)
        json_path, csv_path = write_reports(report, report_dir)
    except Exception as exc:  # never fail silently
        print(f"VALIDATION CRASHED: {exc}", file=sys.stderr)
        return 1

    print_issues(report)
    print("-" * 72)
    print(f"reports: {json_path}")
    print(f"         {csv_path}")

    return 1 if report.status == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
