# OCR Challenge – Evaluator Kit (internal)

Do not share this folder with applicants.

| File | Purpose |
| --- | --- |
| `evaluate.py`, `normalize.py` | Same scoring scripts applicants receive. |
| `leaderboard.py` | Collects all `results/*.json` into a ranked `leaderboard.csv` (automatic 40 points only). |
| `scoring_sheet.xlsx` | Combines automatic points and both reviewers' rubric scores into the final ranking. |

## Run order

```bash
# Hidden set layout: hidden/page_01.png + hidden/page_01.txt, ...
for d in submissions/*/; do
  name=$(basename "$d")
  python -m venv "envs/$name" && "envs/$name/bin/pip" install -r "$d/requirements.txt" pillow rapidfuzz
  "envs/$name/bin/python" evaluate.py --submission "$d" --data hidden/ --out "results/$name.json"
done
python leaderboard.py results/ --out leaderboard.csv
```

Download model weights in a first online pass, then disconnect the network for the scored run.
Keep the GPU otherwise idle so latency stays comparable.

## Scoring sheet

1. **Scores** tab: enter applicant names, run status, WER, CER and median latency from `leaderboard.csv`
   (WER/CER as fractions, e.g. 0.12). Accuracy and Speed points are calculated.
2. **Reviewer 1** / **Reviewer 2** tabs: each reviewer fills their own rubric scores per criterion.
3. **Scores** tab then shows averages, total out of 100, rank, and flags reviewer gaps over 8 points.
4. After walkthrough calls, record pass / concern / fail for each interviewer; a "fail" turns the row red.

Thresholds (points, latency limits, reviewer gap, tie margin) live on the **Settings** tab.
Row 6 is an example applicant; clear its values before use.
