"""
FastAPI Web Application & API for AI OCR BOM Renaming and Landing Page.
Compatible with Railway cloud deployment and local execution.
"""

import os
import io
import zipfile
import uuid
import time
from typing import List, Optional
import cv2
import numpy as np
from PIL import Image, ImageOps

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import AppConfig
from app.ocr_engine import OCREngine
from app.filename_extractor import FilenameExtractor
from app.image_processor import ImageProcessor
from app.rename_manager import RenameManager

app = FastAPI(title="AI OCR BOM Document Renamer", version="2.0.0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# In-memory session cache for ZIP downloads: session_id -> { "files": [(new_name, file_bytes)], "records": [...] }
SESSIONS = {}


def process_uploaded_file_bytes(file_name: str, file_bytes: bytes, config: AppConfig):
    """Processes in-memory file bytes, returns (img_matrix, original_name, ext)."""
    ext = os.path.splitext(file_name)[1].lower()

    if ext == ".pdf":
        try:
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(file_bytes)
            try:
                if len(pdf) > 0:
                    page = pdf.get_page(0)
                    try:
                        bmp = page.render(scale=1.5)
                        pil_img = bmp.to_pil()
                        if pil_img.mode != "RGB":
                            pil_img = pil_img.convert("RGB")
                        rgb_arr = np.array(pil_img)
                        bgr_arr = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)
                        return bgr_arr, ext
                    finally:
                        page.close()
            finally:
                pdf.close()
        except Exception as e:
            print(f"[WebScan] Error rendering PDF {file_name}: {e}")
            return None, ext

    # Standard Images
    try:
        with Image.open(io.BytesIO(file_bytes)) as pil_img:
            pil_img = ImageOps.exif_transpose(pil_img)
            if pil_img.mode != "RGB":
                pil_img = pil_img.convert("RGB")
            rgb_arr = np.array(pil_img)
            bgr_arr = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)
            return bgr_arr, ext
    except Exception:
        try:
            np_arr = np.frombuffer(file_bytes, dtype=np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            return img, ext
        except Exception as e:
            print(f"[WebScan] Error decoding image {file_name}: {e}")
            return None, ext


@app.get("/", response_class=HTMLResponse)
async def serve_landing_page(request: Request):
    """Renders the modern landing page and online web tool."""
    html_path = os.path.join(TEMPLATES_DIR, "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)


@app.post("/api/scan")
async def scan_files(
    files: List[UploadFile] = File(...),
    regex_pattern: str = Form(r"[0-9A-Za-z]{6,15}-[0-9]{2}"),
    min_length: int = Form(8),
    max_length: int = Form(25),
    prefix: str = Form(""),
    suffix: str = Form(""),
    case_format: str = Form("AS_IS"),
):
    """Runs PaddleOCR on batch uploaded files and extracts BOM codes."""
    if not files:
        raise HTTPException(status_code=400, detail="Không có tệp nào được tải lên.")

    config = AppConfig()
    config.regex_pattern = regex_pattern.strip() or r"[0-9A-Za-z]{6,15}-[0-9]{2}"
    config.min_length = min_length
    config.max_length = max_length
    config.prefix = prefix
    config.suffix = suffix
    config.case_format = case_format

    extractor = FilenameExtractor(config)
    ocr_engine = OCREngine.get_instance(lang="ch", use_angle_cls=True)

    session_id = str(uuid.uuid4())
    results = []
    session_files = []
    used_names = set()

    for idx, f in enumerate(files):
        file_name = f.filename or f"document_{idx+1}"
        file_bytes = await f.read()

        bgr_img, ext = process_uploaded_file_bytes(file_name, file_bytes, config)

        if bgr_img is None:
            results.append({
                "id": idx + 1,
                "original_name": file_name,
                "code": "---",
                "bom_type": "Không rõ",
                "new_filename": file_name,
                "confidence": 0.0,
                "status": "Lỗi mở tệp",
                "candidates_count": 0,
            })
            continue

        try:
            # Preprocess and OCR
            processed_img = ImageProcessor.preprocess_for_ocr(bgr_img, config)
            ocr_res = ocr_engine.recognize(processed_img)
            all_texts = [text for _, text, _ in ocr_res]

            candidates = extractor.extract_candidates(ocr_res)
            bom_type = extractor.detect_bom_type(ocr_res)

            best_code = candidates[0].code if candidates else ""
            conf = candidates[0].confidence if candidates else 0.0

            # Calculate conflict-safe new name
            if best_code:
                base_name = f"{prefix}{best_code}{suffix}"
                if case_format == "UPPER":
                    base_name = base_name.upper()
                elif case_format == "LOWER":
                    base_name = base_name.lower()

                target_name = f"{base_name}{ext}"
                target_lower = target_name.lower()

                # Conflict resolution
                if target_lower in used_names:
                    counter = 1
                    while True:
                        cand_name = f"{base_name}_{counter}{ext}"
                        if cand_name.lower() not in used_names:
                            target_name = cand_name
                            break
                        counter += 1

                used_names.add(target_name.lower())
                status = "Nhận diện thành công"
            else:
                target_name = file_name
                status = "Không tìm thấy mã"

            results.append({
                "id": idx + 1,
                "original_name": file_name,
                "code": best_code or "---",
                "bom_type": bom_type or "BOM 1",
                "new_filename": target_name,
                "confidence": round(conf * 100, 1),
                "status": status,
                "candidates_count": len(candidates),
            })

            session_files.append({
                "new_filename": target_name,
                "original_name": file_name,
                "code": best_code,
                "bom_type": bom_type or "BOM 1",
                "confidence": conf,
                "status": status,
                "file_bytes": file_bytes,
            })

        except Exception as e:
            print(f"[WebScan] Error processing {file_name}: {e}")
            results.append({
                "id": idx + 1,
                "original_name": file_name,
                "code": "---",
                "bom_type": "Không rõ",
                "new_filename": file_name,
                "confidence": 0.0,
                "status": f"Lỗi OCR: {str(e)[:50]}",
                "candidates_count": 0,
            })

    # Cache for ZIP download
    SESSIONS[session_id] = {
        "files": session_files,
        "created_at": time.time()
    }

    # Clean up old sessions (>1 hour)
    now = time.time()
    for sid in list(SESSIONS.keys()):
        if now - SESSIONS[sid]["created_at"] > 3600:
            del SESSIONS[sid]

    return JSONResponse({
        "session_id": session_id,
        "total": len(files),
        "results": results,
    })


@app.get("/api/download-zip/{session_id}")
async def download_renamed_zip(session_id: str):
    """Creates a downloadable ZIP containing renamed files and a CSV report."""
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Phiên làm việc đã hết hạn hoặc không tồn tại.")

    session_data = SESSIONS[session_id]
    files = session_data["files"]

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # 1. Add all renamed files
        for f in files:
            zip_file.writestr(f["new_filename"], f["file_bytes"])

        # 2. Add CSV audit report with utf-8-sig
        import csv
        csv_buffer = io.StringIO()
        fieldnames = ["original_filename", "bom_type", "extracted_number", "new_filename", "confidence", "status"]
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
        writer.writeheader()
        for f in files:
            writer.writerow({
                "original_filename": f["original_name"],
                "bom_type": f["bom_type"],
                "extracted_number": f["code"],
                "new_filename": f["new_filename"],
                "confidence": f"{f['confidence']:.1%}",
                "status": f["status"],
            })

        zip_file.writestr("bao_cao_doi_ten.csv", ("\ufeff" + csv_buffer.getvalue()).encode("utf-8"))

    zip_buffer.seek(0)
    zip_filename = f"BOM_Renamed_Files_{time.strftime('%Y%m%d_%H%M%S')}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={zip_filename}"},
    )


@app.get("/download/desktop-app")
async def download_desktop_app():
    """Serves the built standalone Windows .exe if available."""
    exe_path = os.path.join(os.path.dirname(BASE_DIR), "dist", "AI_OCR_Rename_Tool.exe")
    if os.path.exists(exe_path):
        return FileResponse(
            exe_path,
            media_type="application/octet-stream",
            filename="AI_OCR_Rename_Tool.exe",
        )
    return JSONResponse(
        status_code=404,
        content={"message": "File .EXE đang được đóng gói trên máy chủ. Bạn có thể tự build bằng lệnh: python build_exe.py"},
    )
