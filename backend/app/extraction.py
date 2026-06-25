import base64
import json
import os
import re
from typing import Dict, Any

from dotenv import load_dotenv
from PIL import Image
import pytesseract
from openai import OpenAI

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

from app.models import ExtractedLabelFields

load_dotenv()


EXTRACTION_PROMPT = """
You are extracting structured data from an alcohol beverage label for a compliance verification prototype.

Return ONLY valid JSON with these fields:
{
  "brand_name": string or null,
  "class_type": string or null,
  "alcohol_content": string or null,
  "net_contents": string or null,
  "producer_name_address": string or null,
  "country_of_origin": string or null,
  "government_warning": string or null,
  "raw_text": string
}

Rules:
- Do not invent values.
- Preserve wording and punctuation where possible.
- Government warning must be copied exactly as visible.
- If a field is not visible, return null.
"""


def _guess_fields_from_raw_text(raw_text: str) -> ExtractedLabelFields:
    """
    Lightweight local fallback for demo purposes.
    This is intentionally conservative and does not invent missing fields.
    """
    text = raw_text or ""
    upper = text.upper()

    alcohol = None
    alcohol_match = re.search(r"(\d+(?:\.\d+)?\s*%\s*(?:ALC\.?/VOL\.?|ABV)?(?:\s*\(\s*\d+(?:\.\d+)?\s*PROOF\s*\))?|\d+(?:\.\d+)?\s*PROOF)", upper)
    if alcohol_match:
        alcohol = alcohol_match.group(0)

    net_contents = None
    net_match = re.search(r"(\d+(?:\.\d+)?)\s*(ML|MILLILITERS|MILLILITER|L|LITER|LITERS)", upper)
    if net_match:
        net_contents = net_match.group(0)

    government_warning = None
    warning_idx = upper.find("GOVERNMENT WARNING")
    if warning_idx >= 0:
        government_warning = text[warning_idx: warning_idx + 450]

    # Heuristic: first non-empty line may be brand.
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    brand_name = lines[0] if lines else None

    return ExtractedLabelFields(
        brand_name=brand_name,
        class_type=None,
        alcohol_content=alcohol,
        net_contents=net_contents,
        government_warning=government_warning,
        raw_text=raw_text,
        extraction_method="local_tesseract_heuristic"
    )


def extract_with_tesseract(file_path: str) -> ExtractedLabelFields:
    image = Image.open(file_path)
    raw_text = pytesseract.image_to_string(image)
    return _guess_fields_from_raw_text(raw_text)


def _safe_json_parse(content: str) -> Dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def extract_with_openai_vision(file_path: str) -> ExtractedLabelFields:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    client = OpenAI(api_key=api_key)

    with open(file_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": EXTRACTION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{encoded}"
                        },
                    },
                ],
            }
        ],
    )

    content = response.choices[0].message.content or "{}"
    data = _safe_json_parse(content)
    data["extraction_method"] = "openai_vision"
    return ExtractedLabelFields(**data)


def extract_label_fields(file_path: str) -> ExtractedLabelFields:
    use_openai = os.getenv("USE_OPENAI_VISION", "false").lower() == "true"

    if use_openai:
        try:
            return extract_with_openai_vision(file_path)
        except Exception as exc:
            return ExtractedLabelFields(
                raw_text="",
                extraction_method=f"openai_vision_failed: {str(exc)}"
            )

    return extract_with_tesseract(file_path)
