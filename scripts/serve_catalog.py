#!/usr/bin/env python3
"""NightEyes local catalog viewer (no external APIs).

Serves a small local web interface to query the dataset catalog:
    - summary counters (domains, access, licenses, compatibility)
    - filterable dataset table
    - full metadata detail per dataset

Usage:
    python scripts/serve_catalog.py [--port 8765] [--root PROJECT_ROOT]

Then open: http://127.0.0.1:8765/
"""

from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd

INTERFACE_DIR = Path(__file__).resolve().parent.parent / "interface"


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, keep_default_na=False)


class CatalogData:
    """Loads catalog CSVs and answers query/summary requests."""

    def __init__(self, root: Path):
        self.root = Path(root)
        catalog = self.root / "data" / "catalog"
        self.datasets = _read_csv(catalog / "datasets.csv")
        self.compat = _read_csv(catalog / "compatibility_matrix.csv")
        self.licenses = _read_csv(catalog / "licenses.csv")

    # -- helpers ----------------------------------------------------------
    def _compat_levels_for(self, dataset_id: str) -> set:
        if self.compat.empty:
            return set()
        rows = self.compat[self.compat["dataset_id"] == dataset_id]
        return set(rows["compatibility_level"]) if not rows.empty else set()

    def _needs_reannotation(self, dataset_id: str) -> bool:
        if self.compat.empty:
            return False
        rows = self.compat[
            (self.compat["dataset_id"] == dataset_id)
            & (self.compat["requires_reannotation"] == "YES")
        ]
        return not rows.empty

    # -- API --------------------------------------------------------------
    def summary(self) -> dict:
        total = len(self.datasets)
        by_domain: dict = {}
        by_access: dict = {}
        for _, row in self.datasets.iterrows():
            d = row.get("primary_domain", "UNKNOWN")
            a = row.get("access_status", "UNKNOWN")
            by_domain[d] = by_domain.get(d, 0) + 1
            by_access[a] = by_access.get(a, 0) + 1

        license_pending = sum(
            1 for _, r in self.datasets.iterrows()
            if "UNKNOWN" in str(r.get("license", "")).upper()
        )
        direct = partial = 0
        reannotation = 0
        for _, r in self.datasets.iterrows():
            levels = self._compat_levels_for(r["dataset_id"])
            if "DIRECT" in levels:
                direct += 1
            if "PARTIAL" in levels:
                partial += 1
            if self._needs_reannotation(r["dataset_id"]):
                reannotation += 1

        return {
            "total_datasets": total,
            "by_domain": by_domain,
            "by_access": by_access,
            "access_available": by_access.get("AVAILABLE", 0),
            "access_requires_permission":
                by_access.get("REQUIRES_PERMISSION", 0),
            "access_review_required": by_access.get("REVIEW_REQUIRED", 0),
            "license_pending": license_pending,
            "compat_direct_datasets": direct,
            "compat_partial_datasets": partial,
            "needs_reannotation": reannotation,
        }

    def list_datasets(self, filters: dict) -> list:
        df = self.datasets
        if df.empty:
            return []
        out = df.copy()

        q = (filters.get("q") or "").strip().lower()
        if q:
            mask = (
                out["dataset_name"].str.lower().str.contains(q, na=False)
                | out["institution"].str.lower().str.contains(q, na=False)
            )
            out = out[mask]

        for col, key in (
            ("institution", "institution"),
            ("primary_domain", "domain"),
            ("access_status", "access"),
        ):
            value = (filters.get(key) or "").strip()
            if value and col in out.columns:
                out = out[out[col] == value]

        license_f = (filters.get("license") or "").strip()
        if license_f == "PENDING":
            out = out[out["license"].str.upper().str.contains("UNKNOWN",
                                                              na=False)]
        elif license_f == "DEFINED":
            out = out[~out["license"].str.upper().str.contains("UNKNOWN",
                                                               na=False)]

        compat_f = (filters.get("compatibility") or "").strip()
        if compat_f:
            keep = [
                r["dataset_id"] for _, r in out.iterrows()
                if compat_f in self._compat_levels_for(r["dataset_id"])
            ]
            out = out[out["dataset_id"].isin(keep)]

        rows = []
        for _, r in out.iterrows():
            levels = sorted(self._compat_levels_for(r["dataset_id"]))
            rows.append({
                "dataset_id": r["dataset_id"],
                "dataset_name": r["dataset_name"],
                "primary_domain": r["primary_domain"],
                "institution": r["institution"],
                "access_status": r["access_status"],
                "license": r["license"],
                "compatibility_levels": levels,
                "needs_reannotation":
                    self._needs_reannotation(r["dataset_id"]),
            })
        return rows

    def detail(self, dataset_id: str) -> dict | None:
        match = self.datasets[
            self.datasets["dataset_id"] == dataset_id
        ]
        if match.empty:
            return None
        dataset = {k: v for k, v in match.iloc[0].to_dict().items()}
        lic = self.licenses[self.licenses["dataset_id"] == dataset_id]
        license_row = lic.iloc[0].to_dict() if not lic.empty else None
        compat_rows = []
        if not self.compat.empty:
            rows = self.compat[
                self.compat["dataset_id"] == dataset_id
            ]
            compat_rows = [r.to_dict() for _, r in rows.iterrows()]
        return {
            "dataset": dataset,
            "license": license_row,
            "compatibility": compat_rows,
        }


def make_handler(data: CatalogData, interface_dir: Path):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # quiet
            pass

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code: int = 200) -> None:
            body = json.dumps(obj, ensure_ascii=False, indent=2).encode(
                "utf-8")
            self._send(code, body, "application/json; charset=utf-8")

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path
            try:
                if path in ("/", "/index.html"):
                    html = (interface_dir / "index.html").read_bytes()
                    self._send(200, html, "text/html; charset=utf-8")
                    return

                if path == "/api/summary":
                    self._json(data.summary())
                    return

                if path == "/api/datasets":
                    filters = {k: v[0] for k, v in
                               parse_qs(parsed.query).items()}
                    self._json({"datasets": data.list_datasets(filters)})
                    return

                if path.startswith("/api/datasets/"):
                    dataset_id = path.rsplit("/", 1)[-1]
                    detail = data.detail(dataset_id)
                    if detail is None:
                        self._json({"error": "dataset not found"}, 404)
                        return
                    self._json(detail)
                    return

                self._json({"error": "not found"}, 404)
            except Exception as exc:  # never crash silently
                self._json({"error": str(exc)}, 500)

    return Handler


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="NightEyes local catalog viewer")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--root", type=Path,
        default=Path(__file__).resolve().parent.parent,
    )
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    interface_dir = INTERFACE_DIR
    if not (interface_dir / "index.html").exists():
        print(f"ERROR: interface not found at {interface_dir}",
              file=sys.stderr)
        return 1

    try:
        data = CatalogData(root)
    except Exception as exc:
        print(f"ERROR loading catalog: {exc}", file=sys.stderr)
        return 1

    handler = make_handler(data, interface_dir)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"NightEyes catalog viewer: http://{args.host}:{args.port}/")
    print(f"  catalog root: {root}")
    print("  Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
