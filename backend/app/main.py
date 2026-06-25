import os
import tempfile
import time
from dotenv import load_dotenv
import os
load_dotenv()
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models import ApplicationFields, VerificationResponse
from app.extraction import extract_label_fields
from app.verification import verify_label, overall_status


app = FastAPI(
    title="AI-Powered Alcohol Label Verification Assistant",
    description="Prototype for verifying alcohol label artwork against application fields.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check():
    return {
        "status": "ok",
        "message": "Alcohol Label Verification API is running."
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

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload an image file such as PNG or JPG.")

    suffix = os.path.splitext(file.filename or "")[-1] or ".png"

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name

        application = ApplicationFields(
            brand_name=brand_name,
            class_type=class_type,
            alcohol_content=alcohol_content,
            net_contents=net_contents,
            producer_name_address=producer_name_address,
            country_of_origin=country_of_origin,
        )

        extracted = extract_label_fields(tmp_path)
        checks = verify_label(application, extracted)
        elapsed = time.perf_counter() - start

        return VerificationResponse(
            overall_status=overall_status(checks),
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
