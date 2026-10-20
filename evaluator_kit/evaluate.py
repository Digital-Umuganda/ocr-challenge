"""Official scoring script for the OCR challenge.

Applicants and evaluators use this exact file. Only the data folder differs.

    python evaluate.py --submission my_submission/ --data sample/ --out results.json

Data folder layout:
    page_01.png, page_02.png, ...      page images (200 DPI, RGB)
    page_01.txt, page_02.txt, ...      per-page ground truth (preferred), OR
    ground_truth.txt                   one file with the whole document's text

What it does:
  1. Starts your predict.py in a separate process and calls load_model() once
     (limit: LOAD_TIMEOUT_S, not timed for latency).
  2. Runs one untimed warm-up call on the first page.
  3. Calls predict() on every page and times each call (limit: PAGE_TIMEOUT_S).
  4. Normalizes predictions and ground truth with normalize.py.
  5. Reports WER, CER, median latency and the leaderboard points.

Requires: pip install pillow rapidfuzz   (rapidfuzz is optional but much faster)
"""

import argparse
import importlib.util
import json
import multiprocessing as mp
import platform
import statistics
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalize import normalize  # noqa: E402

LOAD_TIMEOUT_S = 600     # 10 minutes for load_model()
PAGE_TIMEOUT_S = 120     # hard limit per page
SPEED_FULL_S = 10.0      # full speed points at or below this median latency
SPEED_ZERO_S = 60.0      # zero speed points at or above this median latency
ACCURACY_POINTS = 30
SPEED_POINTS = 10


# --------------------------------------------------------------------------- metrics

def edit_distance(ref: list, hyp: list) -> int:
    """Levenshtein distance between two sequences (words or characters)."""
    try:
        from rapidfuzz.distance import Levenshtein
        return Levenshtein.distance(ref, hyp)
    except ImportError:
        prev = list(range(len(hyp) + 1))
        for i, r in enumerate(ref, start=1):
            cur = [i] + [0] * len(hyp)
            for j, h in enumerate(hyp, start=1):
                cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h))
            prev = cur
        return prev[-1]


def error_rates(pairs: list[tuple[str, str]]) -> dict:
    """Corpus-level WER and CER: total edits / total reference length."""
    w_err = w_ref = c_err = c_ref = 0
    for ref, hyp in pairs:
        ref_n, hyp_n = normalize(ref), normalize(hyp)
        rw, hw = ref_n.split(), hyp_n.split()
        w_err += edit_distance(rw, hw)
        w_ref += len(rw)
        c_err += edit_distance(list(ref_n), list(hyp_n))
        c_ref += len(ref_n)
    return {
        "wer": w_err / max(w_ref, 1),
        "cer": c_err / max(c_ref, 1),
        "ref_words": w_ref,
        "ref_chars": c_ref,
    }


def accuracy_points(wer: float) -> float:
    """30 x max(0, 1 - 2 x WER): 10% WER -> 24 pts, >= 50% WER -> 0 pts."""
    return round(ACCURACY_POINTS * max(0.0, 1.0 - 2.0 * wer), 2)


def speed_points(median_s: float) -> float:
    """Full points at <= 10 s/page, linear down to 0 at >= 60 s/page."""
    if median_s <= SPEED_FULL_S:
        return float(SPEED_POINTS)
    if median_s >= SPEED_ZERO_S:
        return 0.0
    frac = (SPEED_ZERO_S - median_s) / (SPEED_ZERO_S - SPEED_FULL_S)
    return round(SPEED_POINTS * frac, 2)


# --------------------------------------------------------------------------- worker

def _worker(submission_dir: str, conn) -> None:
    """Runs inside a child process so a hang or crash can be stopped cleanly."""
    try:
        sys.path.insert(0, submission_dir)
        spec = importlib.util.spec_from_file_location("submission_predict", Path(submission_dir) / "predict.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        model = module.load_model()
        conn.send(("loaded", None))
    except Exception:
        conn.send(("error", traceback.format_exc()))
        return

    from PIL import Image

    while True:
        path = conn.recv()
        if path is None:
            return
        try:
            img = Image.open(path).convert("RGB")
            t0 = time.perf_counter()
            text = module.predict(model, img)
            elapsed = time.perf_counter() - t0
            if not isinstance(text, str):
                raise TypeError(f"predict() must return str, got {type(text).__name__}")
            conn.send(("ok", (text, elapsed)))
        except Exception:
            conn.send(("error", traceback.format_exc()))


class Runner:
    def __init__(self, submission_dir: Path):
        ctx = mp.get_context("spawn")
        self.conn, child = ctx.Pipe()
        self.proc = ctx.Process(target=_worker, args=(str(submission_dir.resolve()), child), daemon=True)
        self.proc.start()

    def _wait(self, timeout: float, what: str):
        if not self.conn.poll(timeout):
            raise TimeoutError(f"{what} exceeded {timeout:.0f} s")
        try:
            status, payload = self.conn.recv()
        except EOFError:
            code = self.proc.exitcode
            raise RuntimeError(f"{what} failed: process died (exit code {code}, e.g. out of memory or segfault)")
        if status == "error":
            raise RuntimeError(f"{what} failed:\n{payload}")
        return payload

    def load(self):
        t0 = time.perf_counter()
        self._wait(LOAD_TIMEOUT_S, "load_model()")
        return time.perf_counter() - t0

    def predict(self, path: Path):
        self.conn.send(str(path))
        return self._wait(PAGE_TIMEOUT_S, f"predict() on {path.name}")

    def close(self):
        try:
            self.conn.send(None)
        except Exception:
            pass
        self.proc.join(timeout=5)
        if self.proc.is_alive():
            self.proc.kill()


# --------------------------------------------------------------------------- data

def load_data(data_dir: Path):
    pages = sorted(data_dir.glob("page_*.png"))
    if not pages:
        sys.exit(f"No page_*.png files found in {data_dir}")
    per_page = [p.with_suffix(".txt") for p in pages]
    if all(t.exists() for t in per_page):
        refs = [t.read_text(encoding="utf-8") for t in per_page]
        return pages, refs, "per_page"
    whole = data_dir / "ground_truth.txt"
    if whole.exists():
        return pages, [whole.read_text(encoding="utf-8")], "whole_document"
    sys.exit(f"No ground truth found in {data_dir} (need page_XX.txt files or ground_truth.txt)")


# --------------------------------------------------------------------------- main

def evaluate(submission: Path, data: Path) -> dict:
    pages, refs, gt_mode = load_data(data)
    result = {
        "submission": submission.resolve().name,
        "data": str(data),
        "num_pages": len(pages),
        "ground_truth_mode": gt_mode,
        "machine": {"python": platform.python_version(), "platform": platform.platform()},
        "status": "ok",
        "error": None,
    }
    try:
        import torch
        if torch.cuda.is_available():
            result["machine"]["gpu"] = torch.cuda.get_device_name(0)
    except Exception:
        pass

    preds, times = [], []
    runner = Runner(submission)
    try:
        result["load_seconds"] = round(runner.load(), 2)
        runner.predict(pages[0])  # warm-up, not timed
        for p in pages:
            text, elapsed = runner.predict(p)
            preds.append(text)
            times.append(elapsed)
            print(f"  {p.name}: {elapsed:6.2f} s, {len(text.split())} words")
    except (TimeoutError, RuntimeError) as e:
        result["status"] = "failed"
        result["error"] = str(e)
        print(f"FAILED: {e}", file=sys.stderr)
    finally:
        runner.close()

    if result["status"] == "ok":
        if gt_mode == "per_page":
            pairs = list(zip(refs, preds))
        else:
            pairs = [(refs[0], "\n".join(preds))]
        rates = error_rates(pairs)
        median = statistics.median(times)
        acc = accuracy_points(rates["wer"])
        result.update({
            "wer": round(rates["wer"], 4),
            "cer": round(rates["cer"], 4),
            "ref_words": rates["ref_words"],
            "median_latency_s": round(median, 3),
            "mean_latency_s": round(statistics.mean(times), 3),
            "accuracy_points": acc,
            # Speed only counts if the output is usable: no speed points at WER >= 50%.
            "speed_points": speed_points(median) if acc > 0 else 0.0,
        })
        if gt_mode == "per_page":
            result["per_page"] = [
                {"page": p.name, "latency_s": round(t, 3), **{k: round(v, 4) for k, v in error_rates([(r, h)]).items() if k in ("wer", "cer")}}
                for p, r, h, t in zip(pages, refs, preds, times)
            ]
    else:
        result.update({"wer": None, "cer": None, "median_latency_s": None,
                       "accuracy_points": 0.0, "speed_points": 0.0})

    result["predictions"] = {p.name: t for p, t in zip(pages, preds)}
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description="Score an OCR submission.")
    ap.add_argument("--submission", type=Path, required=True, help="folder containing predict.py")
    ap.add_argument("--data", type=Path, required=True, help="folder with page_XX.png and ground truth")
    ap.add_argument("--out", type=Path, default=Path("results.json"))
    args = ap.parse_args()

    if not (args.submission / "predict.py").exists():
        sys.exit(f"{args.submission}/predict.py not found")

    res = evaluate(args.submission, args.data)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n" + "-" * 40)
    print(f"Status:           {res['status']}")
    if res["status"] == "ok":
        print(f"WER:              {res['wer']:.2%}")
        print(f"CER:              {res['cer']:.2%}")
        print(f"Median latency:   {res['median_latency_s']:.2f} s/page")
        print(f"Accuracy points:  {res['accuracy_points']} / {ACCURACY_POINTS}")
        print(f"Speed points:     {res['speed_points']} / {SPEED_POINTS}")
    print(f"Full results:     {args.out}")


if __name__ == "__main__":
    main()
