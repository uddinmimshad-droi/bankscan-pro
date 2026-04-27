# BankScan Pro

BankScan Pro extracts transactions from bank statement PDFs, including mixed PDFs where some pages are digital text and others are scanned images. It exports the parsed transactions to a formatted Excel workbook with a transaction sheet and summary sheet.

## Features

- React + Tailwind upload UI with drag-and-drop PDF support
- FastAPI backend with CORS enabled for local deployment
- Hybrid extraction: `pdfplumber` first, Tesseract OCR fallback per page
- OCR page conversion through `pdf2image` at 300 DPI
- Regex and heuristic transaction parser for common bank statement formats
- Formatted `.xlsx` export with frozen headers, number formats, colors, totals, and summary metrics
- Job status endpoints for live progress and page-by-page processing messages

## Project Structure

```text
bankscan-pro/
├── backend/
│   ├── main.py
│   ├── pdf_reader.py
│   ├── parser.py
│   ├── excel_exporter.py
│   ├── requirements.txt
│   └── utils.py
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── api.js
    │   └── components/
    ├── package.json
    └── tailwind.config.js
```

## System Dependencies

### Tesseract OCR

Windows:

1. Install from the UB Mannheim build: https://github.com/UB-Mannheim/tesseract/wiki
2. Add the install directory to `PATH`, commonly:
   `C:\Program Files\Tesseract-OCR`
3. Verify:
   `tesseract --version`

macOS:

```bash
brew install tesseract
tesseract --version
```

Linux:

```bash
sudo apt update
sudo apt install tesseract-ocr
tesseract --version
```

### Poppler

`pdf2image` requires Poppler.

Windows:

1. Download Poppler for Windows from https://github.com/oschwartz10612/poppler-windows/releases
2. Add the `Library\bin` folder to `PATH`
3. Verify:
   `pdftoppm -h`

macOS:

```bash
brew install poppler
pdftoppm -h
```

Linux:

```bash
sudo apt install poppler-utils
pdftoppm -h
```

## Backend Setup

```bash
cd bankscan-pro/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

On macOS/Linux, activate the virtual environment with:

```bash
source .venv/bin/activate
```

## Frontend Setup

```bash
cd bankscan-pro/frontend
npm install
npm run dev
```

Open the Vite URL, usually:

```text
http://localhost:5173
```

If your backend runs elsewhere, create `frontend/.env`:

```text
VITE_API_BASE_URL=http://localhost:8000
```

## API Endpoints

- `POST /upload` accepts a PDF and returns `job_id`, file metadata, and page count
- `GET /status/{job_id}` returns progress, page status, stats, warnings, and errors
- `GET /preview/{job_id}` returns the first 20 parsed transactions
- `GET /download/{job_id}` downloads the generated Excel workbook

## Notes on Accuracy

Bank statements vary heavily by bank and layout. The parser is designed to avoid silently inventing rows: it requires a date and at least a transaction amount plus balance, joins continuation lines into particulars, skips repeated headers/noise, de-duplicates identical rows, and flags balance/date anomalies while still exporting the row.

For production use with a specific bank, add sample PDFs and tune `parser.py` with bank-specific row patterns. That is the best way to approach the "zero skipped transactions" requirement across real-world statement layouts.
