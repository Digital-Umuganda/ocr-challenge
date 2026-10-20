"""Collect evaluate.py results into one ranked leaderboard (evaluators only).

    python leaderboard.py results/ --out leaderboard.csv

Ranks by automatic points (Accuracy + Speed), then by lower CER.
These are only 40 of 100 points: copy them into scoring_sheet.xlsx,
where reviewer scores are added and the final ranking is computed.
"""

import argparse
import csv
import json
from pathlib import Path

COLUMNS = ["rank", "submission", "status", "wer", "cer", "median_latency_s",
           "accuracy_points", "speed_points", "auto_total", "error"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("results_dir", type=Path)
    ap.add_argument("--out", type=Path, default=Path("leaderboard.csv"))
    args = ap.parse_args()

    rows = []
    for f in sorted(args.results_dir.glob("*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        rows.append({
            "submission": f.stem,
            "status": r.get("status"),
            "wer": r.get("wer"),
            "cer": r.get("cer"),
            "median_latency_s": r.get("median_latency_s"),
            "accuracy_points": r.get("accuracy_points", 0.0),
            "speed_points": r.get("speed_points", 0.0),
            "auto_total": round(r.get("accuracy_points", 0.0) + r.get("speed_points", 0.0), 2),
            "error": (r.get("error") or "").splitlines()[0] if r.get("error") else "",
        })

    rows.sort(key=lambda x: (-x["auto_total"], x["cer"] if x["cer"] is not None else 9e9))
    for i, row in enumerate(rows, start=1):
        row["rank"] = i

    with args.out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)

    print(f"{'#':>2}  {'submission':<20} {'WER':>7} {'CER':>7} {'s/page':>7} {'auto':>6}")
    for r in rows:
        fmt = lambda v, p=True: "-" if v is None else (f"{v:.1%}" if p else f"{v:.1f}")
        print(f"{r['rank']:>2}  {r['submission']:<20} {fmt(r['wer']):>7} {fmt(r['cer']):>7} "
              f"{fmt(r['median_latency_s'], False):>7} {r['auto_total']:>6}")
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
