#!/usr/bin/env python3
"""NightEyes — consolidate human frame annotations into auditable ground truth.

    python scripts/consolidate_dataset.py --root . --seed 20261121

Actions (idempotent, originals preserved):
    1. archive filename-derived episode/window drafts under data/_incoming/original_labels/
    2. canonicalize participant_id/session_id of every framed annotation
    3. register the SRC009 still-image sources as participants/sessions
    4. rebuild episodes ONLY from human visual frame observations (Level-A)
    5. rebuild Level-B windows with --annotated-only semantics (3 protocol domains)
    6. emit data/processed/{train,validation,test}.csv split BY PARTICIPANT
    7. write split manifest + honest annotation status report
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from make_windows import PROTOCOL_DOMAINS, WINDOWS_HEADER, build_windows

SPLIT_HEADER = [
    "frame_id", "dataset_id", "participant_id", "session_id", "image_path",
    "frame_sha256", "timestamp_ms", "sleepiness_label",
    "sleepiness_behavior", "sleepiness_confidence", "distraction_label",
    "distraction_behavior", "distraction_confidence", "distraction_gaze",
    "phone_visible",
    "lighting_condition", "occlusion_condition", "face_visible",
    "activity_label", "phone_detection", "face_detection",
    "annotation_notes", "split",
]

FRAME_HEADER = [
    "frame_id", "dataset_id", "source_video", "participant_id", "session_id",
    "timestamp_ms", "domain", "reference_label", "behavior_code",
    "gaze_direction", "phone_visible", "annotator_id", "annotation_confidence",
    "lighting_condition", "occlusion_condition", "face_visible", "annotation_notes",
    "activity_label", "phone_detection", "face_detection",
]

PARTICIPANT_HEADER = [
    "participant_id", "dataset_id", "original_participant_id", "anonymized_id",
    "consent_status", "demographic_metadata_availability",
]

SESSION_HEADER = [
    "session_id", "participant_id", "dataset_id", "original_session_id",
    "video_filename", "duration_ms", "original_fps", "resolution",
    "lighting_condition", "camera_position", "glasses_condition",
    "occlusion_condition", "activity_type",
]

EPISODE_HEADER = [
    "episode_id", "session_id", "participant_id", "dataset_id", "start_ms",
    "end_ms", "domain", "behavior_code", "reference_label", "annotator_id",
    "annotation_confidence", "lighting_condition", "occlusion_condition",
    "annotation_notes",
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


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _norm_session(value: str) -> str:
    value = (value or "").strip()
    for ext in (".avi", ".AVI", ".mp4", ".jpg", ".jpeg", ".JPG"):
        if value.endswith(ext):
            value = value[: -len(ext)]
    return value


def _occlusion_from_notes(row: dict) -> str:
    notes = (row.get("annotation_notes") or "").lower()
    if "sunglasses" in notes or "reflective glasses" in notes:
        return "SUNGLASSES"
    if "hand covers" in notes or "hand covering" in notes:
        return "HAND"
    if "occluded" in notes or "obscured" in notes:
        return "PARTIAL"
    return row.get("occlusion_condition") or "NONE"


BEHAVIOR_ALIASES = {
    "GAZE_DEVIATION": "DIST_005",
    "MOUTH_OPEN": "SLEEP_005",
    "EYES_CLOSED": "SLEEP_006",
    "HAND_MOVEMENT": "DIST_006",
}


def _behavior_from_row(row: dict) -> str:
    code = (row.get("behavior_code") or "").strip()
    return BEHAVIOR_ALIASES.get(code, code)


def _lighting_from_row(row: dict) -> str:
    value = (row.get("lighting_condition") or "").strip()
    if value == "DAYLIGHT" and row.get("dataset_id") == "SRC003":
        return "UNVERIFIED_DAYLIGHT"
    return value or "UNKNOWN"


def archive_drafts(ann: Path, original_labels: Path) -> list[str]:
    archived = []
    for name in ("episodes.csv", "windows.csv"):
        src = ann / name
        dst = original_labels / name.replace(".csv", "_draft_auto.csv")
        if src.exists() and not dst.exists():
            original_labels.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            archived.append(dst.name)
    return archived


def canonicalize(root: Path) -> dict:
    ann = root / "data" / "annotation"
    frames_path = ann / "frame_annotations.csv"
    frames = _read(frames_path)
    sessions = _read(ann / "sessions.csv")
    participants = _read(ann / "participants.csv")
    samples = {r["frame_id"]: r for r in _read(root / "data" / "catalog" / "frame_samples.csv")}

    session_by_orig = {_norm_session(r["original_session_id"]): r for r in sessions}

    new_participants: dict[str, dict] = {}
    new_sessions: dict[str, dict] = {}
    still_datasets = ("SRC009", "SRC010")
    max_part = {
        ds: max((int(p["participant_id"].split("_")[-1]) for p in participants
                 if p["participant_id"].startswith(f"PT_{ds}_")), default=0)
        for ds in still_datasets
    }
    max_sess = {
        ds: max((int(s["session_id"].split("_")[-1]) for s in sessions
                 if s["session_id"].startswith(f"SS_{ds}_")), default=0)
        for ds in still_datasets
    }

    updated = []
    for row in frames:
        row = dict(row)
        fid = row["frame_id"]
        if row["dataset_id"] == "SRC003":
            if row["session_id"].startswith("SS_SRC003_"):
                sess = next((s for s in sessions
                             if s["session_id"] == row["session_id"]), None)
            else:
                sess = session_by_orig.get(_norm_session(row["session_id"]))
            if sess is None:
                raise SystemExit(f"no canonical session for frame {fid}: {row['session_id']}")
            row["session_id"] = sess["session_id"]
            row["participant_id"] = sess["participant_id"]
        elif row["dataset_id"] in still_datasets:
            ds = row["dataset_id"]
            source = f"{ds}:{row['source_video']}"
            if source not in new_participants:
                existing = next((p for p in participants
                                 if p.get("dataset_id") == ds
                                 and p.get("original_participant_id") == source), None)
                if existing is None:
                    max_part[ds] += 1
                    existing = {
                        "participant_id": f"PT_{ds}_{max_part[ds]:03d}",
                        "dataset_id": ds,
                        "original_participant_id": source,
                        "anonymized_id": f"A{ds[-2:]}_{max_part[ds]:03d}",
                        "consent_status": "DOCUMENTED_PUBLIC_LICENSE",
                        "demographic_metadata_availability": "UNKNOWN",
                    }
                    participants.append(existing)
                new_participants[source] = existing
            if source not in new_sessions:
                existing_s = next((s for s in sessions
                                   if s.get("dataset_id") == ds
                                   and s.get("original_session_id") == source), None)
                if existing_s is None:
                    max_sess[ds] += 1
                    sample = samples.get(fid, {})
                    existing_s = {
                        "session_id": f"SS_{ds}_{max_sess[ds]:04d}",
                        "participant_id": new_participants[source]["participant_id"],
                        "dataset_id": ds,
                        "original_session_id": source,
                        "video_filename": row["source_video"],
                        "duration_ms": "1000",
                        "original_fps": "0",
                        "resolution": f"{sample.get('width', '?')}x{sample.get('height', '?')}",
                        "lighting_condition": row.get("lighting_condition") or "UNKNOWN",
                        "camera_position": "UNKNOWN",
                        "glasses_condition": "UNKNOWN",
                        "occlusion_condition": _occlusion_from_notes(row),
                        "activity_type": "STILL_IMAGE",
                    }
                    sessions.append(existing_s)
                new_sessions[source] = existing_s
            row["participant_id"] = new_participants[source]["participant_id"]
            row["session_id"] = new_sessions[source]["session_id"]
        else:
            raise SystemExit(f"unexpected dataset_id {row['dataset_id']} in frame {fid}")

        row["occlusion_condition"] = _occlusion_from_notes(row)
        row["lighting_condition"] = _lighting_from_row(row)
        row["behavior_code"] = _behavior_from_row(row)
        row["face_visible"] = row.get("face_visible") or "UNKNOWN"
        updated.append(row)

    _write(ann / "participants.csv", PARTICIPANT_HEADER, participants)
    _write(ann / "sessions.csv", SESSION_HEADER, sessions)
    _write(frames_path, FRAME_HEADER, updated)

    return {
        "frames": updated,
        "new_participants": len(new_participants),
        "new_sessions": len(new_sessions),
    }


def rebuild_episodes(root: Path, frames: list[dict]) -> list[dict]:
    ann = root / "data" / "annotation"
    rows = []
    for i, f in enumerate(frames, start=1):
        ts = int(f["timestamp_ms"])
        note = (
            "HUMAN VISUAL FRAME OBSERVATION (Level-A point unit) | "
            f"catalog {f['frame_id']} | {f.get('annotation_notes', '')}"
        ).strip()
        rows.append({
            "episode_id": f"EP_H{i:06d}",
            "session_id": f["session_id"],
            "participant_id": f["participant_id"],
            "dataset_id": f["dataset_id"],
            "start_ms": str(ts),
            "end_ms": str(ts + 1),
            "domain": f["domain"],
            "behavior_code": f.get("behavior_code") or "",
            "reference_label": f["reference_label"],
            "annotator_id": f.get("annotator_id") or "ANN_1",
            "annotation_confidence": f.get("annotation_confidence") or "MEDIUM",
            "lighting_condition": f["lighting_condition"],
            "occlusion_condition": f["occlusion_condition"],
            "annotation_notes": note,
        })
    _write(ann / "episodes.csv", EPISODE_HEADER, rows)
    return rows


def rebuild_windows(root: Path) -> list[dict]:
    ann = root / "data" / "annotation"
    rows = build_windows(
        root,
        window_ms=5000,
        annotator="ANN_1",
        domains=PROTOCOL_DOMAINS,
        annotated_only=True,
    )
    for r in rows:
        r["annotation_notes"] = (
            "derived from human frame observations (annotated-only); "
            + r["annotation_notes"]
        )
    _write(ann / "windows.csv", WINDOWS_HEADER, rows)
    return rows


def make_splits(root: Path, frames: list[dict], seed: int) -> dict:
    samples = {r["frame_id"]: r for r in _read(root / "data" / "catalog" / "frame_samples.csv")}
    by_frame: dict[str, dict] = {}
    for f in frames:
        rec = by_frame.setdefault(f["frame_id"], {
            "frame_id": f["frame_id"],
            "dataset_id": f["dataset_id"],
            "participant_id": f["participant_id"],
            "session_id": f["session_id"],
            "image_path": samples[f["frame_id"]]["frame_file"],
            "frame_sha256": samples[f["frame_id"]]["frame_sha256"],
            "timestamp_ms": f["timestamp_ms"],
        })
        prefix = "sleepiness" if f["domain"] == "SLEEPINESS" else "distraction"
        rec[f"{prefix}_label"] = f["reference_label"]
        rec[f"{prefix}_behavior"] = f.get("behavior_code") or ""
        rec[f"{prefix}_confidence"] = f.get("annotation_confidence") or ""
        if f["domain"] == "DISTRACTION":
            rec["distraction_gaze"] = f.get("gaze_direction") or ""
            rec["phone_visible"] = f.get("phone_visible") or ""
        rec["lighting_condition"] = f["lighting_condition"]
        rec["occlusion_condition"] = f["occlusion_condition"]
        rec["face_visible"] = f.get("face_visible") or "UNKNOWN"
        rec["activity_label"] = f.get("activity_label") or "UNKNOWN"
        rec["phone_detection"] = f.get("phone_detection") or "UNKNOWN"
        rec["face_detection"] = f.get("face_detection") or "UNKNOWN"
        rec["annotation_notes"] = f.get("annotation_notes") or ""

    participants = sorted({r["participant_id"] for r in by_frame.values()})

    def assign(pid: str) -> str:
        digest = hashlib.sha256(f"{seed}:{pid}".encode("utf-8")).hexdigest()
        value = int(digest[:8], 16) % 100
        if value < 70:
            return "TRAIN"
        if value < 85:
            return "VALIDATION"
        return "TEST"

    assignment = {pid: assign(pid) for pid in participants}
    for split, idx in (("VALIDATION", 0), ("TEST", 1)):
        if not any(v == split for v in assignment.values()):
            assignment[participants[idx % len(participants)]] = split

    processed = root / "data" / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for split in ("TRAIN", "VALIDATION", "TEST"):
        name = split.lower()
        rows = [dict(rec, split=split) for rec in by_frame.values()
                if assignment[rec["participant_id"]] == split]
        rows.sort(key=lambda r: r["frame_id"])
        path = processed / f"{name}.csv"
        _write(path, SPLIT_HEADER, rows)
        outputs[split] = {
            "path": path.relative_to(root).as_posix(),
            "frames": len(rows),
            "participants": len({r["participant_id"] for r in rows}),
            "sha256": _sha256(path),
        }

    manifest = {
        "protocol": "NightEyes V0.1 §8",
        "seed": seed,
        "method": "deterministic sha256(seed:participant_id) group split",
        "ratios": {"TRAIN": 70, "VALIDATION": 15, "TEST": 15},
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "test_locked": True,
        "test_lock_note": "TEST must not be used for calibration until final evaluation.",
        "splits": outputs,
        "participants_total": len(participants),
        "frames_total": len(by_frame),
        "disjoint_by_participant": True,
    }
    (processed / "split_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def write_status(root: Path, manifest: dict, episodes: list[dict],
                 windows: list[dict], archived: list[str]) -> None:
    reports = root / "data" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    domains = defaultdict(int)
    labels = defaultdict(int)
    phone_counts = defaultdict(int)
    face_counts = defaultdict(int)
    for ep in episodes:
        domains[ep["domain"]] += 1
        labels[ep["reference_label"]] += 1
    frames = _read(root / "data" / "annotation" / "frame_annotations.csv")
    for row in frames:
        if row["domain"] != "SLEEPINESS":
            continue
        phone_counts[row.get("phone_visible") or "UNKNOWN"] += 1
        face_counts[row.get("face_visible") or "UNKNOWN"] += 1
    lines = [
        "# NightEyes — status da anotação e do ground truth",
        "",
        f"Gerado em {datetime.now(timezone.utc).isoformat(timespec='seconds')}.",
        "",
        "## O que é ground truth observado",
        "",
        f"- {len(episodes)} unidades Level-A derivadas de anotação visual humana "
        "de frames catalogados (não de nomes de arquivo nem de scores do motor).",
        f"- {len(windows)} janelas Level-B de 5 s apenas onde há episódio anotado; "
        "nenhum rótulo ABSENT fabricado para material não revisado.",
        "- Rótulos UNCERTAIN/UNOBSERVABLE preservados (nunca convertidos em ABSENT).",
        "",
        "## Arquivos preservados (rascunhos)",
        "",
        *[f"- `data/_incoming/original_labels/{p.name}` — rascunho local por filename; "
          "não usar para avaliação e não versionado."
          for p in sorted((root / "data" / "_incoming" / "original_labels").glob("*_draft_auto.csv"))
          if p.exists()],
        "",
        "## Divisão por participante (protocolo §8)",
        "",
        f"- Semente: `{manifest['seed']}`; participantes: {manifest['participants_total']}.",
        *[f"- {k}: {v['frames']} frames / {v['participants']} participantes (`{v['path']}`)"
          for k, v in manifest["splits"].items()],
        "- TEST está bloqueado para calibração (`test_locked=true`).",
        "",
        "## Limitações conhecidas (declaradas, não ocultadas)",
        "",
        "- **Avaliação cega dupla pendente**: apenas ANN_1 produziu anotações visuais; "
        "ANN_2 não tem linhas. Um segundo avaliador independente é necessário "
        "antes de uso como referência final.",
        "- **Fadiga**: episódios UNCERTAIN de frame isolado (sem persistência observável); "
        "critérios em `documentation/fatigue_criteria.md`. Nenhum episódio "
        "FATIGUE=PRESENT fabricado.",
        "- **KSS/autorrelato**: esquema `data/annotation/self_reports.csv` criado, "
        "sem registros (fonte atual não fornece KSS).",
        "- **Episódios pontuais**: cada unidade Level-A cobre apenas o frame observado "
        "(`end_ms = start_ms + 1`); extensão temporal não foi inferida.",
        "- **Iluminação SRC003**: `UNVERIFIED_DAYLIGHT` indica valor herdado do lote, "
        "não verificado quadro a quadro.",
        "- **Consentimento SRC009/SRC010**: imagens públicas sob CC BY 4.0 / MIT "
        "(`DOCUMENTED_PUBLIC_LICENSE`), sem consentimento individual documentado. "
        "SRC010 descarta rótulos EAR/MAR da fonte (protocolo §7).",
        "",
        "## Distribuição de rótulos nos episódios",
        "",
        *[f"- {k}: {v}" for k, v in sorted(labels.items())],
        "",
        "## Domínios",
        "",
        *[f"- {k}: {v} episódios" for k, v in sorted(domains.items())],
        "",
        "## Detecção de rosto e celular (por frame catalogado)",
        "",
        *[f"- face_visible={k}: {v}" for k, v in sorted(face_counts.items())],
        *[f"- phone_visible={k}: {v}" for k, v in sorted(phone_counts.items())],
        "- `phone_visible=YES` sozinho nunca gera `DISTRACTION=PRESENT` (protocolo §2.3).",
        "- 50 candidatos SRC009 (rótulo-fonte 'Object') foram revisados visualmente; "
        "13 confirmados como celular, o restante são garrafas/copos (falso positivo da fonte).",
        "- Amostragem densa (0.2..0.8) adicionada aos vídeos 5-FemaleGlasses para capturar "
        "bocejos reais que a amostragem 0.1/0.5/0.9 não alcançava.",
        "",
    ]
    (reports / "annotation_status.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Consolidate NightEyes human annotations")
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--seed", type=int, default=20261121)
    args = ap.parse_args(argv)
    root = args.root.resolve()

    archived = archive_drafts(root / "data" / "annotation",
                              root / "data" / "_incoming" / "original_labels")
    canon = canonicalize(root)
    episodes = rebuild_episodes(root, canon["frames"])
    windows = rebuild_windows(root)
    manifest = make_splits(root, canon["frames"], args.seed)
    write_status(root, manifest, episodes, windows, archived)

    print(f"canonicalized {len(canon['frames'])} frame annotations "
          f"({canon['new_participants']} SRC009 participants, "
          f"{canon['new_sessions']} SRC009 sessions)")
    print(f"rebuilt {len(episodes)} human episodes and {len(windows)} annotated windows")
    for split, meta in manifest["splits"].items():
        print(f"{split}: {meta['frames']} frames / {meta['participants']} participants")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
