"""Submission template. Copy this file into your submission folder and fill it in.

The evaluator imports this file and calls, in order:
    model = load_model()                 # once, not timed (limit: 10 minutes)
    text  = predict(model, page_image)   # once per page, timed (limit: 120 s/page)

Rules:
  - `page_image` is ONE page as an RGB PIL.Image rendered at 200 DPI.
  - Return plain text for that page, lines separated by "\n".
  - Weights may be downloaded from Hugging Face inside load_model().
    The scoring run itself happens OFFLINE, after a download pass.
  - No paid APIs, no hard-coded text from the sample page.
"""

from PIL import Image


def load_model() -> object:
    """Load every model your pipeline needs and return them in one object.

    Example (replace with your own pipeline):

        from transformers import AutoProcessor, AutoModelForVision2Seq
        processor = AutoProcessor.from_pretrained("<model-id>")
        model = AutoModelForVision2Seq.from_pretrained("<model-id>").to("cuda").eval()
        return {"processor": processor, "model": model}
    """
    return None


def predict(model: object, image: Image.Image) -> str:
    """Return the full text of one page image."""
    # Replace this placeholder with your pipeline.
    return ""


if __name__ == "__main__":
    # Quick self-test: python predict.py path/to/page.png
    import sys

    m = load_model()
    img = Image.open(sys.argv[1]).convert("RGB")
    print(predict(m, img))
