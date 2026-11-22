#!/usr/bin/env python3
"""Ultra-review: build a categorized, audited copy of every cataloged image.

    python scripts/build_categorized_catalog.py --root .

Creates the canonical `fotos catalogadas/<categoria>/` tree:
    normal | sonolencia | fadiga | bocejo | olhos_fechados | usando_celular

An image may appear in more than one folder (multi-label): a yawn with closed
eyes belongs to both `bocejo` and `olhos_fechados`. The manifest records the
complete per-image label set and the audit result of the cross-checks.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
import tempfile
from collections import defaultdict
from pathlib import Path

CATEGORIES = (
    "normal", "sonolencia", "fadiga", "bocejo",
    "olhos_fechados", "usando_celular",
)
MANIFEST_FIELDS = [
    "frame_id", "dataset_id", "original_filename", "image", "renamed_files",
    "categories", "activity_label",
    "sleepiness_label", "sleepiness_behavior", "fatigue_label",
    "distraction_label", "phone_detection", "face_detection", "audit",
]


def _read(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build categorized catalog")
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = ap.parse_args(argv)
    root = args.root.resolve()
    samples = _read(root / "data" / "catalog" / "frame_samples.csv")
    ann = _read(root / "data" / "annotation" / "frame_annotations.csv")
    out = root / "fotos catalogadas"
    tmp = tempfile.TemporaryDirectory()
    tmp_dir = Path(tmp.name)
    source_copy = {}
    for sample in samples:
        fid = sample["frame_id"]
        src = Path(sample.get("original_frame_file") or sample["frame_file"])
        if not src.exists():
            src = Path(sample["frame_file"])
        if src.exists():
            dest = tmp_dir / f"{fid}{src.suffix.lower()}"
            shutil.copyfile(src, dest)
            source_copy[fid] = dest
    shutil.rmtree(out, ignore_errors=True)
    for cat in CATEGORIES:
        (out / cat).mkdir(parents=True, exist_ok=True)

    by_frame: dict[str, dict] = {}
    for row in ann:
        rec = by_frame.setdefault(row["frame_id"], {"frame_id": row["frame_id"]})
        rec["dataset_id"] = row["dataset_id"]
        if row["domain"] == "SLEEPINESS":
            rec["sleepiness_label"] = row["reference_label"]
            rec["sleepiness_behavior"] = row.get("behavior_code") or ""
            rec["activity_label"] = row.get("activity_label") or "UNKNOWN"
        elif row["domain"] == "FATIGUE":
            rec["fatigue_label"] = row["reference_label"]
        elif row["domain"] == "DISTRACTION":
            rec["distraction_label"] = row["reference_label"]
        rec["phone_detection"] = row.get("phone_detection") or "UNKNOWN"
        rec["face_detection"] = row.get("face_detection") or "UNKNOWN"

    manifest = []
    audit_issues = []
    copied = defaultdict(int)
    assignments = []
    for sample in samples:
        fid = sample["frame_id"]
        rec = by_frame.get(fid)
        if rec is None:
            audit_issues.append(f"{fid}: sem anotação humana")
            continue
        categories = []
        beh = rec.get("sleepiness_behavior", "")
        label = rec.get("sleepiness_label", "")
        phone = rec.get("phone_detection", "")
        act = rec.get("activity_label", "")

        if phone == "YES":
            categories.append("usando_celular")
        if beh == "SLEEP_003":
            categories.append("bocejo")
        if beh in ("SLEEP_001", "SLEEP_006") or act == "DROWSY":
            categories.append("olhos_fechados")
        if label in ("PRESENT", "UNCERTAIN"):
            categories.insert(0, "sonolencia")
        if rec.get("fatigue_label") in ("PRESENT", "UNCERTAIN") and \
                beh in ("SLEEP_001", "SLEEP_006"):
            categories.append("fadiga")
        if not categories:
            categories.append("normal")

        checks = []
        if phone == "YES" and act == "PHONE_USE" and \
                rec.get("distraction_label") == "PRESENT":
            checks.append("ERRO: presença de celular gerou distração PRESENT")
        if beh == "SLEEP_003" and act not in ("YAWNING", "UNKNOWN"):
            checks.append("aviso: bocejo sem atividade YAWNING")
        if beh in ("SLEEP_001", "SLEEP_006") and label != "PRESENT":
            checks.append("aviso: código de olho fechado com rótulo diferente de PRESENT")
        audit = "OK" if not checks else "; ".join(checks)
        if any(c.startswith("ERRO") for c in checks):
            audit_issues.append(f"{fid}: {audit}")

        src = source_copy.get(fid, Path(sample["frame_file"]))
        if not src.exists():
            audit_issues.append(f"{fid}: arquivo de imagem ausente ({sample['frame_file']})")
        elif _sha256(src) != sample["frame_sha256"]:
            audit_issues.append(f"{fid}: SHA-256 da imagem não confere com catálogo")
        assignments.append((sample, rec, categories, audit, src))

    renamed = {}
    for sample, rec, categories, audit, src in assignments:
        if not src.exists():
            continue
        for cat in categories:
            copied[cat] += 1
            dest = out / cat / f"{cat}_{copied[cat]:04d}{src.suffix.lower()}"
            shutil.copyfile(src, dest)
            renamed[(sample["frame_id"], cat)] = dest
        manifest.append({
            "frame_id": sample["frame_id"], "dataset_id": sample["dataset_id"],
            "original_filename": (
                sample.get("original_filename")
                or Path(sample.get("original_frame_file") or sample["frame_file"]).name
            ),
            "image": renamed[(sample["frame_id"], categories[0])].relative_to(root).as_posix(),
            "categories": "|".join(categories),
            "renamed_files": "|".join(
                renamed[(sample["frame_id"], c)].relative_to(root).as_posix() for c in categories
            ),
            "activity_label": rec.get("activity_label", ""),
            "sleepiness_label": rec.get("sleepiness_label", ""),
            "sleepiness_behavior": rec.get("sleepiness_behavior", ""),
            "fatigue_label": rec.get("fatigue_label", ""),
            "distraction_label": rec.get("distraction_label", ""),
            "phone_detection": rec.get("phone_detection", ""),
            "face_detection": rec.get("face_detection", ""),
            "audit": audit,
        })

    with (out / "manifest.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=MANIFEST_FIELDS)
        w.writeheader()
        w.writerows(manifest)

    readme = [
        "# Fotos catalogadas — categorias",
        "",
        f"Total de frames catalogados: **{len(samples)}**. Cada imagem foi copiada "
        "para uma ou mais pastas abaixo, conforme rótulos de anotação humana "
        "(Level-A frame observation).",
        "",
        *[f"- `{c}/` — {copied[c]} imagens (`{c}_0001.jpg`, `{c}_0002.jpg`, ...)"
          for c in CATEGORIES],
        "",
        "## Nomenclatura",
        "",
        "Cada arquivo foi renomeado para `categoria_NNNN.ext` em ordem de `frame_id`. "
        "O nome original e o `frame_id` estão preservados em `manifest.csv` "
        "(colunas `original_filename`, `frame_id` e `renamed_files`).",
        "",
        "## Regras de inclusão",
        "",
        "- `normal`: sem sonolência, fadiga, bocejo, olho fechado ou celular detectado.",
        "- `sonolencia`: rótulo PRESENT/UNCERTAIN de sonolência sem código específico "
        "de bocejo/olho fechado.",
        "- `fadiga`: olho fechado observado em frame isolado (UNCERTAIN por falta de "
        "persistência temporal — ver `documentation/fatigue_criteria.md`).",
        "- `bocejo`: somente `SLEEP_003` confirmado por revisão visual.",
        "- `olhos_fechados`: `SLEEP_001` / `SLEEP_006` ou atividade DROWSY.",
        "- `usando_celular`: `phone_detection=YES` após verificação visual em tamanho real; "
        "a presença de celular sozinha nunca gera `DISTRACTION=PRESENT` (§2.3).",
        "",
        f"Auditoria cruzada: **{len(audit_issues)}** problema(s) encontrado(s).",
        *[f"- {i}" for i in audit_issues[:50]],
        "",
    ]
    (out / "README.md").write_text("\n".join(readme), encoding="utf-8")
    for cat in CATEGORIES:
        print(f"{cat}: {copied[cat]}")
    print(f"manifest: {len(manifest)} frames; auditoria: {len(audit_issues)} problema(s)")
    tmp.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
