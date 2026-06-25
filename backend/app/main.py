import os
import tempfile
import time
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models import ApplicationFields, VerificationResponse
from app.extraction import extract_label_fields
from app.verification import verify_label, overall_status

load_dotenv()

app = FastAPI(
    title="AI-Powered Alcohol Label Verification Assistant",
    description="Prototype for verifying alcohol label artwork against application fields.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://alcohol-label-verifier.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check():
    return {
        "status": "ok",
        "message": "Alcohol Label Verification API is running.",
    }


@app.get("/debug/config")
def debug_config():
    return {
        "ocr_provider": os.getenv("OCR_PROVIDER"),
        "use_openai_vision": os.getenv("USE_OPENAI_VISION"),
        "use_llm_parser": os.getenv("USE_LLM_PARSER"),
        "groq_model": os.getenv("GROQ_MODEL"),
        "has_ocrspace_key": bool(os.getenv("OCRSPACE_API_KEY")),
        "has_groq_key": bool(os.getenv("GROQ_API_KEY")),
    }


@app.post("/api/verify", response_model=VerificationResponse)
async def verify_label_endpoint(
    file: UploadFile = File(...),
    brand_name: str = Form(...),
    class_type: str = Form(...),
    alcohol_content: str = Form(...),
    net_contents: str = Form(...),
    producer_name_address: Optional[str] = Form(None),
    country_of_origin: Optional[str] = Form(None),
):
    start = time.perf_counter()

    print("=" * 80, flush=True)
    print("VERIFY REQUEST RECEIVED", flush=True)
    print("Filename:", file.filename, flush=True)
    print("Content Type:", file.content_type, flush=True)
    print("OCR_PROVIDER:", os.getenv("OCR_PROVIDER"), flush=True)
    print("USE_LLM_PARSER:", os.getenv("USE_LLM_PARSER"), flush=True)
    print("GROQ_MODEL:", os.getenv("GROQ_MODEL"), flush=True)
    print("Has OCR.space key:", bool(os.getenv("OCRSPACE_API_KEY")), flush=True)
    print("Has Groq key:", bool(os.getenv("GROQ_API_KEY")), flush=True)

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Please upload an image file such as PNG or JPG.",
        )

    suffix = os.path.splitext(file.filename or "")[-1] or ".png"

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name

        print("Uploaded file size bytes:", len(contents), flush=True)

        application = ApplicationFields(
            brand_name=brand_name,
            class_type=class_type,
            alcohol_content=alcohol_content,
            net_contents=net_contents,
            producer_name_address=producer_name_address,
            country_of_origin=country_of_origin,
        )

        print("Application Fields:", application.model_dump(), flush=True)

        extracted = extract_label_fields(tmp_path)

        print("-" * 80, flush=True)
        print("EXTRACTION RESULT", flush=True)
        print("Extraction Method:", extracted.extraction_method, flush=True)
        print("Brand:", extracted.brand_name, flush=True)
        print("Class/Type:", extracted.class_type, flush=True)
        print("Alcohol:", extracted.alcohol_content, flush=True)
        print("Net Contents:", extracted.net_contents, flush=True)
        print("Producer:", extracted.producer_name_address, flush=True)
        print("Country:", extracted.country_of_origin, flush=True)
        print("Government Warning Found:", bool(extracted.government_warning), flush=True)
        print("Raw OCR Text:", flush=True)
        print(extracted.raw_text or "[EMPTY OCR TEXT]", flush=True)
        print("-" * 80, flush=True)

        checks = verify_label(application, extracted)
        final_status = overall_status(checks)
        elapsed = time.perf_counter() - start

        print("VERIFICATION RESULT:", final_status, flush=True)
        for check in checks:
            print(
                f"{check.field}: {check.status} | expected={check.expected} | found={check.found} | score={check.score}",
                flush=True,
            )
        print("=" * 80, flush=True)

        return VerificationResponse(
            overall_status=final_status,
            checks=checks,
            extracted_fields=extracted,
            processing_time_seconds=round(elapsed, 3),
            metadata={
                "filename": file.filename,
                "content_type": file.content_type,
                "size_bytes": len(contents),
            },
        )

    finally:
        try:
            if "tmp_path" in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass