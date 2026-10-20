# OCR Challenge – Starter Kit

Everything you need to score your own work exactly the way we will.

| File | Purpose |
| --- | --- |
| `predict.py` | Template with the required `load_model()` / `predict()` interface. Copy it into your submission folder and fill it in. |
| `evaluate.py` | The official scoring script. Identical to ours; only the test pages differ. |
| `normalize.py` | Text normalization applied before scoring. Do not modify. |
| `prepare_sample.py` | Converts `sample.pdf` + `sample_ground_truth.docx` into the format `evaluate.py` reads. |
| `requirements.txt` | Packages needed by these scripts (not by your model). |

## Quick start

```bash
pip install -r requirements.txt

# 1. Convert the sample into page images + ground truth text
python prepare_sample.py --pdf sample.pdf --docx sample_ground_truth.docx --out sample/

# 2. Copy the template and build your pipeline in it
mkdir -p my_submission && cp predict.py my_submission/

# 3. Score yourself
python evaluate.py --submission my_submission/ --data sample/ --out results.json
```

## What `evaluate.py` measures

- **WER / CER**: corpus-level error rates after normalization (lowercase, no punctuation, whitespace collapsed).
- **Latency**: median seconds per page after one untimed warm-up page. `load_model()` time is excluded.
- **Points**: Accuracy = 30 × max(0, 1 − 2 × WER); Speed = 10 at ≤ 10 s/page, falling linearly to 0 at 60 s/page. Speed points are only given when WER is below 50% (i.e. Accuracy > 0).

Your code runs in a separate process. A page that takes longer than 120 s, or any crash, marks the run as failed.

The sample score is for your own feedback only. The official score uses hidden pages on our machine.
