#!/usr/bin/env python3
"""NightEyes — licensed acquisition pipeline.

Gate of legality first: every source must be cleared in
data/catalog/licenses.csv before any download starts.

Usage:
    python scripts/acquire.py list
    python scripts/acquire.py fetch SRC003
    python scripts/acquire.py finalize SRC003
    python scripts/acquire.py extract SRC003
    python scripts/acquire.py register

Flow:
    list      -> show channels + legal gate per dataset
    fetch     -> download into data/_incoming/<DATASET>/ (staging, resumable)
    finalize  -> verify size, move into data/raw/<DATASET>/, SHA-256,
                 append to data/catalog/sources_registry.csv
    extract   -> untar/unrar/ unzip archives in place (idempotent: each
                 archive gets a .extracted_* marker) and register products
    register  -> scan data/raw for unregistered files and hash them
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
INCOMING = ROOT / "data" / "_incoming"
LICENSES = ROOT / "data" / "catalog" / "licenses.csv"
REGISTRY = ROOT / "data" / "catalog" / "sources_registry.csv"
TODAY = date.today().isoformat()

# Acquisition channels. "cleared" channels may only be used when the license
# gate below returns CLEARED for the dataset.
SOURCES: dict[str, dict] = {
    "SRC003": {
        "name": "YawDD",
        "dir": "YawDD",
        "files": {
            "user06.tar": {
                "url": "http://skuld.cs.umass.edu/traces/mmsys/2014/user06.tar",
                "expected_bytes": 5307791360,
                "channel": "UMass MMSys 2014 academic mirror (referenced by QUALINET)",
                "official": "https://ieee-dataport.org/open-access/yawdd-yawning-detection-dataset",
            }
        },
    },
    "SRC002": {
        "name": "UTA-RLDD",
        "dir": "UTA_RLDD",
        "files": {
            "UTA_RLDD_official_drive": {
                "url": "https://drive.google.com/drive/folders/1d_QwgpMXnLY_FmLYXDn7TLcw0D-svXEl",
                "expected_bytes": None,
                "channel": "Official public Google Drive (authors' page)",
                "official": "https://sites.google.com/view/utarldd/home",
            }
        },
    },
    "SRC005": {
        "name": "NTHU-DDD",
        "dir": "NTHU_DDD",
        "files": {
            "NTHU-DDD_official": {
                "url": "http://cv.cs.nthu.edu.tw/php/callforpaper/datasets/DDD/",
                "expected_bytes": None,
                "channel": "Official EULA + e-mail request",
                "official": "http://cv.cs.nthu.edu.tw/php/callforpaper/datasets/DDD/",
            }
        },
    },
    "SRC007": {
        "name": "STATE-FARM",
        "dir": "State_Farm",
        "files": {
            "state-farm-kaggle": {
                "url": "https://www.kaggle.com/competitions/state-farm-distracted-driver-detection/data",
                "expected_bytes": None,
                "channel": "Kaggle competition (accept rules)",
                "official": "https://www.kaggle.com/competitions/state-farm-distracted-driver-detection/data",
            }
        },
    },
    "SRC001": {
        "name": "DMD",
        "dir": "DMD",
        "files": {
            "DMD_official_forms": {
                "url": "https://dmd.vicomtech.org/",
                "expected_bytes": None,
                "channel": "Official download forms (opendatasets.vicomtech.org)",
                "official": "https://dmd.vicomtech.org/",
            }
        },
    },
    "SRC008": {
        "name": "UL-DD",
        "dir": "UL_DD",
        "files": {
            "UL-DD_zenodo": {
                "url": "https://zenodo.org/records/17978727",
                "expected_bytes": None,
                "channel": "Zenodo restricted (institutional e-mail)",
                "official": "https://zenodo.org/records/17978727",
            }
        },
    },
    "SRC006": {
        "name": "AUC-DISTRACTED",
        "dir": "AUC_Distracted",
        "files": {
            "AUC_official_license": {
                "url": "https://heshameraqi.github.io/data/auc.distracted.driver.dataset/",
                "expected_bytes": None,
                "channel": "Signed license agreement + e-mail to MI-AUC",
                "official": "https://heshameraqi.github.io/data/auc.distracted.driver.dataset/",
            }
        },
    },
    "SRC004": {
        "name": "DROZY",
        "dir": "DROZY",
        "files": {
            "DROZY_official": {
                "url": "http://drozy.ulg.ac.be/",
                "expected_bytes": None,
                "channel": "Official site (unreachable on 2026-11-19)",
                "official": "http://drozy.ulg.ac.be/",
            }
        },
    },
    "SRC009": {
        "name": "DrowsinessEdge",
        "dir": "DrowsinessEdge",
        "files": {
            "dataset.zip": {
                "url": "https://zenodo.org/records/17317199/files/Drowsiness%20Dataset.zip?download=1",
                "expected_bytes": 1066783719,
                "channel": "Zenodo CC BY 4.0 direct download",
                "official": "https://zenodo.org/records/17317199",
            }
        },
    },
    "SRC010": {
        "name": "AutoLabeledFaceCrops",
        "dir": "AutoLabeledFaceCrops",
        "files": {
            "dataset_page": {
                "url": "https://huggingface.co/datasets/notgoodkeeper/cnn-based-drowsiness-detection-data",
                "expected_bytes": None,
                "channel": "Hugging Face MIT sample (deterministic stride via acquire_hf_facecrops.py)",
                "official": "https://github.com/not-good-keeper/cnn-based-drowsiness-detection",
            }
        },
    },

}


def load_licenses() -> dict[str, dict]:
    out: dict[str, dict] = {}
    with open(LICENSES, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            out[row["dataset_id"]] = row
    return out


def gate(lic: dict | None) -> tuple[str, str]:
    """Return (status, reason). Only CLEARED may be fetched automatically."""
    if lic is None:
        return "BLOCKED", "dataset not in licenses.csv"
    name = (lic.get("license_name") or "").upper()
    perm = (lic.get("permission_required") or "").upper()
    if "UNKNOWN" in name or not name:
        return "BLOCKED", "license UNKNOWN (pending confirmation with authors)"
    if perm.startswith("YES"):
        return "BLOCKED", f"permission required: {lic.get('permission_required')}"
    if "REVIEW" in name or "REVIEW" in (lic.get("permission_required") or "").upper():
        return "BLOCKED", "legal review required"
    if "RESTRICTED" in (lic.get("redistribution_permission") or "").upper():
        return "CLEARED-LOCAL", "use allowed locally; no redistribution"
    return "CLEARED", f"license: {lic.get('license_name')}"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cmd_list() -> int:
    lic_map = load_licenses()
    print(f"{'ID':7} {'DATASET':16} {'GATE':16} DETAIL")
    print("-" * 110)
    for sid, src in SOURCES.items():
        status, reason = gate(lic_map.get(sid))
        print(f"{sid:7} {src['name']:16} {status:16} {reason}")
        for fname, meta in src["files"].items():
            print(f"{'':7} channel: {meta['channel']}")
            print(f"{'':7} url:     {meta['url']}")
    return 0


def cmd_fetch(dataset_id: str) -> int:
    src = SOURCES.get(dataset_id)
    if src is None:
        print(f"ERROR: unknown dataset {dataset_id}")
        return 1
    status, reason = gate(load_licenses().get(dataset_id))
    if status not in ("CLEARED", "CLEARED-LOCAL"):
        print(f"BLOCKED {dataset_id}: {reason}")
        print("No download performed. Clear the license first (see licenses.csv).")
        return 2
    print(f"GATE OK {dataset_id}: {reason}")
    stage = INCOMING / src["dir"]
    stage.mkdir(parents=True, exist_ok=True)
    rc = 0
    for fname, meta in src["files"].items():
        if fname.endswith((".tar", ".zip", ".rar", ".7z")) or "." in fname:
            target = stage / fname
            print(f"fetching {meta['url']} -> {target}")
            cmd = [
                "curl", "-L", "-C", "-", "--retry", "10", "--retry-delay", "5",
                "--fail", "-o", str(target), meta["url"],
            ]
            rc = subprocess.call(cmd)
            if rc != 0:
                print(f"curl exited {rc} (resumable: re-run fetch)")
                return rc
            size = target.stat().st_size
            exp = meta.get("expected_bytes")
            if exp and size != exp:
                print(f"WARNING: size {size} != expected {exp}")
                return 3
            print(f"OK {fname}: {size} bytes")
        else:
            print(f"MANUAL channel (open in browser): {meta['url']}")
    return rc


def next_source_id() -> str:
    ids = []
    if REGISTRY.exists():
        with open(REGISTRY, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                rid = (row.get("source_file_id") or "").strip()
                if rid.startswith("SF") and rid[2:].isdigit():
                    ids.append(int(rid[2:]))
    return f"SF{max(ids, default=0) + 1:03d}"


def append_registry(rows: list[dict]) -> None:
    fieldnames = [
        "source_file_id", "dataset_id", "original_filename", "original_path",
        "checksum_sha256", "file_type", "file_size", "import_date",
        "access_permission", "processing_status",
    ]
    exists = REGISTRY.exists()
    with open(REGISTRY, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerows(rows)


def registered_paths() -> set[str]:
    if not REGISTRY.exists():
        return set()
    with open(REGISTRY, newline="", encoding="utf-8") as fh:
        return {
            (r.get("original_path") or "").strip()
            for r in csv.DictReader(fh)
            if (r.get("original_path") or "").strip()
        }


def cmd_finalize(dataset_id: str) -> int:
    src = SOURCES.get(dataset_id)
    if src is None:
        print(f"ERROR: unknown dataset {dataset_id}")
        return 1
    lic = load_licenses().get(dataset_id)
    status, reason = gate(lic)
    if status == "BLOCKED":
        print(f"BLOCKED {dataset_id}: {reason}")
        return 2
    stage = INCOMING / src["dir"]
    dest = RAW / src["dir"]
    dest.mkdir(parents=True, exist_ok=True)
    if not stage.exists():
        print(f"nothing staged at {stage}")
        return 1
    done = 0
    for item in sorted(stage.iterdir()):
        if item.name == ".gitkeep":
            continue
        exp = src["files"].get(item.name, {}).get("expected_bytes")
        if exp and item.stat().st_size != exp:
            print(f"INCOMPLETE {item.name}: {item.stat().st_size} != {exp} — not finalized")
            continue
        target = dest / item.name
        shutil.move(str(item), str(target))
        digest = sha256_of(target)
        rel = f"data/raw/{src['dir']}/{item.name}"
        append_registry([{
            "source_file_id": next_source_id(),
            "dataset_id": dataset_id,
            "original_filename": item.name,
            "original_path": rel,
            "checksum_sha256": digest,
            "file_type": target.suffix.lstrip(".").lower() or "bin",
            "file_size": str(target.stat().st_size),
            "import_date": TODAY,
            "access_permission": (lic or {}).get("license_name", "UNKNOWN"),
            "processing_status": "REGISTERED",
        }])
        print(f"REGISTERED {rel} sha256={digest[:16]}...")
        done += 1
    if not done:
        print("no complete files to finalize")
        return 1
    return 0


def cmd_register() -> int:
    known = registered_paths()
    added = 0
    if not RAW.exists():
        print("data/raw does not exist")
        return 0
    for path in sorted(RAW.rglob("*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel in known:
            continue
        sid = next((k for k, v in SOURCES.items() if f"/{v['dir']}/" in f"/{rel}"), "SRC000")
        lic = load_licenses().get(sid, {})
        digest = sha256_of(path)
        append_registry([{
            "source_file_id": next_source_id(),
            "dataset_id": sid,
            "original_filename": path.name,
            "original_path": rel,
            "checksum_sha256": digest,
            "file_type": path.suffix.lstrip(".").lower() or "bin",
            "file_size": str(path.stat().st_size),
            "import_date": TODAY,
            "access_permission": lic.get("license_name", "UNKNOWN"),
            "processing_status": "REGISTERED",
        }])
        print(f"REGISTERED {rel} sha256={digest[:16]}...")
        added += 1
    if not added:
        print("all raw files already registered")
    return 0


def _find_tool(candidates: list[str]) -> str | None:
    for c in candidates:
        if Path(c).exists():
            return c
    return None


def cmd_extract(dataset_id: str) -> int:
    """Extract archives in data/raw/<dir> (tar via bsdtar, rar via UnRAR/7z).

    Extraction products are auto-registered (V09) in the same run. The
    original archive is kept untouched (protocol: originals preserved).
    Idempotent: a .extracted_<name> marker (dotfile, ignored by V09/register)
    skips already-processed archives; the scan re-runs in a loop so archives
    nested inside archives (e.g. a .rar inside a .tar) are handled in one run.
    """
    src = SOURCES.get(dataset_id)
    if src is None:
        print(f"ERROR: unknown dataset {dataset_id}")
        return 1
    status, reason = gate(load_licenses().get(dataset_id))
    if status == "BLOCKED":
        print(f"BLOCKED {dataset_id}: {reason}")
        return 2
    base = RAW / src["dir"]
    if not base.exists():
        print(f"nothing at {base}")
        return 1

    unrar = _find_tool([
        r"C:\Program Files\WinRAR\UnRAR.exe",
        r"C:\Program Files (x86)\WinRAR\UnRAR.exe",
    ])
    seven = _find_tool([
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
    ])

    extracted_any = False
    processed: set[Path] = set()
    while True:
        archives = [
            p for p in sorted(base.rglob("*"))
            if p.is_file() and not p.name.startswith(".")
            and p.suffix.lower() in (".tar", ".rar", ".zip")
            and p not in processed
        ]
        if not archives:
            break
        for arch in archives:
            marker = base / f".extracted_{arch.name}"
            if marker.exists():
                processed.add(arch)
                continue
            print(f"extracting {arch.relative_to(ROOT).as_posix()} ...")
            if arch.suffix.lower() == ".tar":
                rc = subprocess.call(["tar", "-xf", str(arch), "-C", str(base)])
            elif arch.suffix.lower() == ".rar":
                if unrar:
                    rc = subprocess.call([unrar, "x", "-o+", "-idq",
                                          str(arch), str(base) + "\\"])
                elif seven:
                    rc = subprocess.call([seven, "x", "-y", f"-o{base}",
                                          f"-w{base}", str(arch)])
                else:
                    print("ERROR: neither UnRAR nor 7-Zip found")
                    return 4
            else:  # .zip
                if seven:
                    rc = subprocess.call([seven, "x", "-y", f"-o{base}",
                                          str(arch)])
                else:
                    import zipfile
                    with zipfile.ZipFile(arch) as zf:
                        zf.extractall(base)
                    rc = 0
            if rc != 0:
                print(f"ERROR: extraction failed for {arch.name} ({rc})")
                return rc
            marker.write_text(TODAY, encoding="utf-8")
            processed.add(arch)
            extracted_any = True

    if not extracted_any:
        print("no archives to extract (already extracted?)")
    else:
        print("extraction done — registering products ...")
    return cmd_register()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="NightEyes licensed acquisition")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    f = sub.add_parser("fetch"); f.add_argument("dataset_id")
    fin = sub.add_parser("finalize"); fin.add_argument("dataset_id")
    ext = sub.add_parser("extract"); ext.add_argument("dataset_id")
    sub.add_parser("register")
    args = p.parse_args(argv)
    if args.cmd == "list":
        return cmd_list()
    if args.cmd == "fetch":
        return cmd_fetch(args.dataset_id)
    if args.cmd == "finalize":
        return cmd_finalize(args.dataset_id)
    if args.cmd == "extract":
        return cmd_extract(args.dataset_id)
    if args.cmd == "register":
        return cmd_register()
    return 1


if __name__ == "__main__":
    sys.exit(main())
