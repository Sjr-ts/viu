#!/usr/bin/env python3
"""Ultra-review: build a categorized, audited copy of every cataloged image.

    python scripts/build_categorized_catalog.py --root .

Creates data/curated/fotos_catalogadas/<categoria>/:
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
from collections import defaultdict
from pathlib import Path

CATEGORIES = (
    "normal", "sonolencia", "fadiga", "bocejo",
    "olhos_fechados", "usando_celular",
)
MANIFEST_FIELDS = [
    "frame_id", "dataset_id", "image", "categories", "activity_label",
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
    out = root / "data" / "curated" / "fotos_catalogadas"
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

        src = Path(sample["frame_file"])
        dest_rel = None
        if src.exists():
            for cat in categories:
                dest = out / cat / src.name
                if not dest.exists():
                    shutil.copyfile(src, dest)
                    copied[cat] += 1
            dest_rel = (out / categories[0] / src.name).relative_to(root).as_posix()
            if _sha256(src) != sample["frame_sha256"]:
                audit_issues.append(f"{fid}: SHA-256 da imagem não confere com catálogo")
        else:
            audit_issues.append(f"{fid}: arquivo de imagem ausente ({sample['frame_file']})")

        manifest.append({
            "frame_id": fid, "dataset_id": sample["dataset_id"],
            "image": dest_rel or "", "categories": "|".join(categories),
            "activity_label": act, "sleepiness_label": label,
            "sleepiness_behavior": beh,
            "fatigue_label": rec.get("fatigue_label", ""),
            "distraction_label": rec.get("distraction_label", ""),
            "phone_detection": phone, "face_detection": rec.get("face_detection", ""),
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
        *[f"- `{c}/` — {copied[c]} imagens" for c in CATEGORIES],
        "",
        "## Regras de inclusão",
        "",
        "- `normal`: sem sonolência, fadiga, bocejo, olho fechado ou celular detectado.",
        "- `sonolencia`: rótulo PRESENT/UNCERTAIN de sonolência sem código específico "
        "de bocejo/olho fechado.",
        "- `fadiga`: olho fechado observado em frame isolado (UNCERTAIN por falta de "
        "persistência temporal — ver `documentation/fatigue_criteria.md`).",
        "- `bocejo`: `SLEEP_003` ou atividade visual YAWNING.",
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
