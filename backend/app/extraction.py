import tempfile
from PIL import Image
from groq import Groq
import requests
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

def extract_fields_with_llm(raw_text: str) -> ExtractedLabelFields:
    api_key = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    if not api_key:
        fallback = _guess_fields_from_raw_text(raw_text)
        fallback.extraction_method = "heuristic_parser_missing_groq_key"
        return fallback

    client = Groq(api_key=api_key)

    prompt = f"""
You are extracting structured fields from OCR text of an alcohol beverage label.

Return ONLY valid JSON with exactly these keys:
brand_name
class_type
alcohol_content
net_contents
producer_name_address
country_of_origin
government_warning
raw_text

Rules:
- Do not invent values.
- If a field is missing, use null.
- Brand name is usually the product/distillery name, not the class/type.
- Class/type examples: Bourbon Whiskey, Kentucky Straight Bourbon Whiskey, Rye Whiskey, Vodka, Gin, Rum, Tequila.
- Alcohol content examples: 45% Alc./Vol. (90 Proof), 40% ABV, 80 Proof.
- Net contents examples: 750 mL, 1 L, 375 mL.
- Government warning starts with GOVERNMENT WARNING if present.
- Preserve wording as closely as possible.

OCR text:
\"\"\"
{raw_text}
\"\"\"
"""

    response = client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "You extract alcohol label fields from OCR text and return strict JSON only."
            },
            {
                "role": "user",
                "content": prompt
            },
        ],
    )

    content = response.choices[0].message.content
    data = json.loads(content)

    return ExtractedLabelFields(
        brand_name=data.get("brand_name"),
        class_type=data.get("class_type"),
        alcohol_content=data.get("alcohol_content"),
        net_contents=data.get("net_contents"),
        producer_name_address=data.get("producer_name_address"),
        country_of_origin=data.get("country_of_origin"),
        government_warning=data.get("government_warning"),
        raw_text=raw_text,
        extraction_method=f"ocrspace_api_plus_groq_{model}",
    )

def extract_with_tesseract(file_path: str) -> ExtractedLabelFields:
    image = Image.open(file_path)
    raw_text = pytesseract.image_to_string(image)
    return _guess_fields_from_raw_text(raw_text)

def prepare_image_for_ocr(file_path: str) -> str:
    image = Image.open(file_path)

    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    max_width = 1600
    max_height = 1600

    image.thumbnail((max_width, max_height))

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    temp_path = temp_file.name
    temp_file.close()

    image.save(temp_path, format="JPEG", quality=75, optimize=True)

    return temp_path

def extract_with_ocrspace(file_path: str) -> ExtractedLabelFields:
    api_key = os.getenv("OCRSPACE_API_KEY", "helloworld")

    ocr_file_path = prepare_image_for_ocr(file_path)

    with open(ocr_file_path, "rb") as image_file:
        response = requests.post(
            "https://api.ocr.space/parse/image",
            files={"file": image_file},
            data={
                "apikey": api_key,
                "language": "eng",
                "OCREngine": 2,
                "scale": "true",
                "isTable": "false",
            },
            timeout=45,
        )

    response.raise_for_status()
    data = response.json()

    if data.get("IsErroredOnProcessing"):
        raise RuntimeError(data.get("ErrorMessage", "OCR.space processing error"))

    parsed_results = data.get("ParsedResults") or []
    raw_text = "\n".join(
        result.get("ParsedText", "")
        for result in parsed_results
        if result.get("ParsedText")
    )

    use_llm_parser = os.getenv("USE_LLM_PARSER", "false").lower() == "true"

    if use_llm_parser:
        return extract_fields_with_llm(raw_text)

    extracted = _guess_fields_from_raw_text(raw_text)
    extracted.extraction_method = "ocrspace_api"
    return extracted


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
    provider = os.getenv("OCR_PROVIDER", "tesseract").lower()
    use_openai = os.getenv("USE_OPENAI_VISION", "false").lower() == "true"

    if use_openai or provider == "openai":
        try:
            return extract_with_openai_vision(file_path)
        except Exception as exc:
            return ExtractedLabelFields(
                raw_text="",
                extraction_method=f"openai_vision_failed: {str(exc)}"
            )

    if provider == "ocrspace":
        try:
            return extract_with_ocrspace(file_path)
        except Exception as exc:
            return ExtractedLabelFields(
                raw_text="",
                extraction_method=f"ocrspace_failed: {str(exc)}"
            )

    try:
        return extract_with_tesseract(file_path)
    except Exception as exc:
        return ExtractedLabelFields(
            raw_text="",
            extraction_method=f"tesseract_failed: {str(exc)}"
        )