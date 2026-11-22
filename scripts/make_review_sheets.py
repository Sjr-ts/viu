#!/usr/bin/env python3
"""Generate labeled contact sheets (montages) from cataloged frames for human review."""
import argparse
import csv
from pathlib import Path

import cv2
import numpy as np

GRID = (4, 3)  # cols, rows
TILE = (360, 240)


def build_sheets(catalog_csv: Path, out_dir: Path, per_sheet: int = GRID[0] * GRID[1]) -> list[Path]:
    rows = list(csv.DictReader(catalog_csv.open(encoding="utf-8")))
    out_dir.mkdir(parents=True, exist_ok=True)
    sheets: list[Path] = []
    cols, rows_n = GRID
    for sidx in range(0, len(rows), per_sheet):
        batch = rows[sidx : sidx + per_sheet]
        tile_w, tile_h = TILE
        canvas = np.zeros((rows_n * tile_h, cols * tile_w, 3), dtype="uint8")
        for i, row in enumerate(batch):
            img = cv2.imread(row["frame_file"])
            if img is None:
                continue
            img = cv2.resize(img, (tile_w, tile_h))
            # label: index within full catalog + frame_id tail
            idx = sidx + i
            label = f"#{idx} {Path(row['frame_file']).stem[:38]}"
            cv2.rectangle(img, (0, 0), (tile_w, 22), (0, 0, 0), -1)
            cv2.putText(img, label, (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 255), 1, cv2.LINE_AA)
            r, c = divmod(i, cols)
            canvas[r * tile_h : (r + 1) * tile_h, c * tile_w : (c + 1) * tile_w] = img
        out_path = out_dir / f"sheet_{sidx // per_sheet:03d}.jpg"
        cv2.imwrite(str(out_path), canvas, [cv2.IMWRITE_JPEG_QUALITY, 88])
        sheets.append(out_path)
    return sheets


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default="data/catalog/frame_samples.csv")
    ap.add_argument("--out", default="data/_incoming/review_sheets")
    args = ap.parse_args()
    sheets = build_sheets(Path(args.catalog), Path(args.out))
    print(f"generated {len(sheets)} sheets in {args.out}")


if __name__ == "__main__":
    main()
