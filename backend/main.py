import shutil
import uuid
from datetime import datetime
import os
from pathlib import Path
from typing import Dict

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from excel_exporter import export_transactions_to_excel
from parser import parse_transactions
from pdf_reader import extract_pdf_text, inspect_pdf


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="BankScan Pro API", version="1.0.0")
cors_origins = os.getenv("CORS_ORIGINS")
allowed_origins = [origin.strip() for origin in cors_origins.split(",")] if cors_origins else [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

jobs: Dict[str, Dict] = {}


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "bankscan-pro-api"}


@app.post("/upload")
async def upload_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    job_id = str(uuid.uuid4())
    pdf_path = UPLOAD_DIR / f"{job_id}.pdf"
    try:
        with pdf_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        page_count = inspect_pdf(pdf_path)
        if page_count > 200:
            raise HTTPException(status_code=400, detail="PDF exceeds the 200 page limit.")
    except PermissionError as exc:
        pdf_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        pdf_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        pdf_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="The PDF is corrupted or unreadable.") from exc

    jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "file_name": file.filename,
        "file_size": pdf_path.stat().st_size,
        "page_count": page_count,
        "current_page": 0,
        "total_pages": page_count,
        "message": "Queued for processing...",
        "progress": 0,
        "created_at": datetime.utcnow().isoformat(),
        "transactions": [],
        "warnings": [],
        "failed_pages": [],
        "pages_processed": 0,
        "ocr_pages": 0,
        "digital_pages": 0,
        "output_path": None,
        "error": None,
    }
    background_tasks.add_task(process_pdf_job, job_id, pdf_path)
    return {
        "job_id": job_id,
        "file_name": file.filename,
        "file_size": pdf_path.stat().st_size,
        "page_count": page_count,
    }


@app.get("/status/{job_id}")
def get_status(job_id: str):
    job = _get_job(job_id)
    safe_job = {key: value for key, value in job.items() if key not in {"transactions", "output_path"}}
    safe_job["transactions_found"] = len(job.get("transactions", []))
    return safe_job


@app.post("/cancel/{job_id}")
def cancel_job(job_id: str):
    job = _get_job(job_id)
    if job["status"] in {"queued", "processing"}:
        job["status"] = "cancelled"
        job["message"] = "Processing cancelled by user."
        job["error"] = "Cancelled by user."
    return {"status": job["status"]}


@app.get("/preview/{job_id}")
def preview_transactions(job_id: str):
    job = _get_job(job_id)
    if job["status"] not in {"completed", "failed"}:
        raise HTTPException(status_code=409, detail="Processing is not complete yet.")
    return {
        "transactions": job.get("transactions", [])[:20],
        "total": len(job.get("transactions", [])),
        "warnings": job.get("warnings", []),
    }


@app.get("/download/{job_id}")
def download_excel(job_id: str):
    job = _get_job(job_id)
    if job["status"] != "completed":
        raise HTTPException(status_code=409, detail="Excel file is not ready yet.")
    output_path = Path(job["output_path"])
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Generated Excel file was not found.")
    return FileResponse(
        output_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"bankscan-pro-{job_id}.xlsx",
    )


def process_pdf_job(job_id: str, pdf_path: Path) -> None:
    job = jobs[job_id]
    try:
        job["status"] = "processing"

        def progress(current_page: int, total_pages: int, message: str) -> None:
            if job["status"] == "cancelled":
                raise InterruptedError("Job was cancelled by the user.")
            job["current_page"] = current_page
            job["total_pages"] = total_pages
            job["message"] = message
            job["progress"] = int((current_page / max(total_pages, 1)) * 70)

        extraction = extract_pdf_text(pdf_path, progress)
        job["message"] = "Parsing transactions..."
        job["progress"] = 80
        page_texts = [(page.page_number, page.text, page.tables) for page in extraction.pages if page.text or page.tables]
        transactions, warnings = parse_transactions(page_texts)
        if not transactions:
            raise ValueError("No transactions were found. Please verify that this is a bank statement PDF.")

        output_path = OUTPUT_DIR / f"{job_id}.xlsx"
        export_transactions_to_excel(
            transactions,
            output_path,
            pages_processed=extraction.total_pages,
            ocr_pages=extraction.ocr_pages,
            digital_pages=extraction.digital_pages,
        )

        job.update(
            {
                "status": "completed",
                "message": "Processing complete.",
                "progress": 100,
                "transactions": [tx.to_dict() for tx in transactions],
                "warnings": warnings,
                "failed_pages": extraction.failed_pages,
                "pages_processed": extraction.total_pages,
                "ocr_pages": extraction.ocr_pages,
                "digital_pages": extraction.digital_pages,
                "output_path": str(output_path),
                "error": None,
            }
        )
    except InterruptedError as exc:
        job.update(
            {
                "status": "failed",
                "message": "Processing cancelled.",
                "progress": 100,
                "error": str(exc),
            }
        )
    except Exception as exc:
        job.update(
            {
                "status": "failed",
                "message": "Processing failed.",
                "progress": 100,
                "error": str(exc),
            }
        )


def _get_job(job_id: str) -> Dict:
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job
