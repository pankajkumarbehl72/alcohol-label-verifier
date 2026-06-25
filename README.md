# AI-Powered Alcohol Label Verification Assistant

A standalone prototype that helps compliance agents verify alcohol beverage label artwork against expected application fields.

The app extracts text from an uploaded label image, compares it against application values, and returns a clear pass / warning / fail review.

## Features

- Upload alcohol label image
- Enter expected application fields
- Extract label text using either:
  - OpenAI Vision API, or
  - local Tesseract OCR fallback
- Verify:
  - Brand name
  - Class/type
  - Alcohol content
  - Net contents
  - Government warning
  - Optional producer/bottler information
  - Optional country of origin
- Human-friendly result screen
- No permanent file storage

## Tech Stack

- Frontend: React + Vite
- Backend: FastAPI
- OCR/AI: OpenAI Vision optional, Tesseract fallback
- Matching: Python rule engine + RapidFuzz

## Project Structure

```text
alcohol-label-verifier/
  backend/
    app/
      main.py
      models.py
      extraction.py
      verification.py
    requirements.txt
  frontend/
    src/
      App.jsx
      components/
      api/
    package.json
  README.md
```

## Backend Setup

From the project root:

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment.

Windows PowerShell:

```bash
.venv\Scripts\Activate.ps1
```

Mac/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create environment file:

```bash
copy .env.example .env
```

On Mac/Linux:

```bash
cp .env.example .env
```

### Optional OpenAI Vision Setup

Edit `backend/.env`:

```env
OPENAI_API_KEY=your_key_here
USE_OPENAI_VISION=true
```

If you do not configure this, the app uses local Tesseract OCR.

### Tesseract Setup

For local OCR fallback, install Tesseract.

Windows:
- Install from the official UB Mannheim Windows installer.
- Add Tesseract to PATH.

Mac:

```bash
brew install tesseract
```

Ubuntu/Debian:

```bash
sudo apt-get install tesseract-ocr
```

Run backend:

```bash
uvicorn app.main:app --reload
```

Backend should be available at:

```text
http://localhost:8000
```

API docs:

```text
http://localhost:8000/docs
```

## Frontend Setup

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend should be available at:

```text
http://localhost:5173
```

## How to Use

1. Start the backend.
2. Start the frontend.
3. Open the frontend URL.
4. Enter application fields.
5. Upload a PNG or JPG label image.
6. Click **Verify Label**.
7. Review pass / warning / fail results.

## Example Distilled Spirits Test Data

Use these application values:

```text
Brand Name: OLD TOM DISTILLERY
Class/Type: Kentucky Straight Bourbon Whiskey
Alcohol Content: 45% Alc./Vol. (90 Proof)
Net Contents: 750 mL
```

Government warning expected text:

```text
GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink alcoholic beverages during pregnancy because of the risk of birth defects. (2) Consumption of alcoholic beverages impairs your ability to drive a car or operate machinery, and may cause health problems.
```

## Design Approach

This prototype is intentionally an **agent assistant**, not an automated approval system.

The goal is to reduce routine manual matching while keeping compliance judgment with the human reviewer.

The app uses:
- OCR/vision extraction to read the label
- deterministic rules for compliance checks
- fuzzy matching for fields where formatting differences should not cause false failures
- strict checking for the government warning statement

## Assumptions

- Prototype is standalone and does not integrate with COLA.
- Uploaded files are processed temporarily and deleted after review.
- The MVP focuses on distilled spirits-style label fields.
- Fuzzy matching is acceptable for brand/class fields.
- Government warning text should be checked strictly.
- Bold/font detection is listed as a prototype limitation.

## Tradeoffs and Limitations

- OCR accuracy depends on image quality.
- Poor lighting, glare, and angled photos may reduce extraction quality.
- The local Tesseract fallback is less accurate than a vision model.
- The prototype does not permanently store submissions.
- The prototype does not make final regulatory decisions.
- Detection of bold text in the warning heading is not implemented in this MVP.

## Future Enhancements

- Batch CSV upload
- PDF label support
- Image preprocessing for glare/rotation
- Confidence thresholds configurable by administrators
- Audit logs
- COLA integration
- Azure deployment with federal compliance controls
- Role-based access control
