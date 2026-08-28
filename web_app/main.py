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

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warmup OCR Engine in background on container startup
    try:
        print("[Startup] Initializing PaddleOCR engine in background...")
        engine = OCREngine.get_instance(lang="ch", use_angle_cls=True)
        dummy_img = np.zeros((64, 64, 3), dtype=np.uint8)
        engine.recognize(dummy_img)
        print("[Startup] PaddleOCR engine ready.")
    except Exception as e:
        print(f"[Startup] Engine warmup notice: {e}")
    yield

app = FastAPI(title="AI OCR BOM Document Renamer", version="2.0.0", lifespan=lifespan)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# In-memory session cache for ZIP downloads: session_id -> { "files": [...], "used_names": set(), "created_at": float }
SESSIONS = {}


def process_uploaded_file_bytes(file_name: str, file_bytes: bytes, config: AppConfig):
    """Processes in-memory file bytes, returns (img_matrix, ext)."""
    ext = os.path.splitext(file_name)[1].lower()

    if ext == ".pdf":
        try:
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(file_bytes)
            try:
                if len(pdf) > 0:
                    page = pdf.get_page(0)
                    try:
                        # scale=1.1 provides optimal balance of OCR precision and low CPU latency
                        bmp = page.render(scale=1.1)
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


@app.get("/favicon.ico", include_in_schema=False)
async def get_favicon():
    favicon_path = os.path.join(STATIC_DIR, "favicon.svg")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path, media_type="image/svg+xml")
    return HTMLResponse("", status_code=204)


@app.get("/", response_class=HTMLResponse)
async def serve_landing_page(request: Request):
    """Renders the modern landing page and online web tool."""
    html_path = os.path.join(TEMPLATES_DIR, "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)


@app.post("/api/scan-single")
async def scan_single_file(
    file: UploadFile = File(...),
    session_id: str = Form(""),
    regex_pattern: str = Form(r"[0-9A-Za-z]{6,15}-[0-9]{2}"),
    min_length: int = Form(8),
    max_length: int = Form(25),
    prefix: str = Form(""),
    suffix: str = Form(""),
    case_format: str = Form("AS_IS"),
):
    """Processes a single file with PaddleOCR and streams result immediately."""
    config = AppConfig()
    config.regex_pattern = regex_pattern.strip() or r"[0-9A-Za-z]{6,15}-[0-9]{2}"
    config.min_length = min_length
    config.max_length = max_length
    config.prefix = prefix
    config.suffix = suffix
    config.case_format = case_format

    extractor = FilenameExtractor(config)
    ocr_engine = OCREngine.get_instance(lang="ch", use_angle_cls=True)

    if not session_id or session_id not in SESSIONS:
        session_id = str(uuid.uuid4())
        SESSIONS[session_id] = {
            "files": [],
            "used_names": set(),
            "created_at": time.time(),
        }

    session_data = SESSIONS[session_id]
    used_names = session_data["used_names"]

    file_name = file.filename or "document"
    file_bytes = await file.read()

    bgr_img, ext = process_uploaded_file_bytes(file_name, file_bytes, config)

    if bgr_img is None:
        result = {
            "session_id": session_id,
            "original_name": file_name,
            "code": "---",
            "bom_type": "Không rõ",
            "new_filename": file_name,
            "confidence": 0.0,
            "status": "Lỗi mở tệp",
            "candidates_count": 0,
        }
        return JSONResponse(result)

    try:
        processed_img = ImageProcessor.preprocess_for_ocr(bgr_img, config)
        ocr_res = ocr_engine.recognize(processed_img)
        candidates = extractor.extract_candidates(ocr_res)
        bom_type = extractor.detect_bom_type(ocr_res)

        best_code = candidates[0].code if candidates else ""
        conf = candidates[0].confidence if candidates else 0.0

        if best_code:
            base_name = f"{prefix}{best_code}{suffix}"
            if case_format == "UPPER":
                base_name = base_name.upper()
            elif case_format == "LOWER":
                base_name = base_name.lower()

            target_name = f"{base_name}{ext}"
            target_lower = target_name.lower()

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

        result = {
            "session_id": session_id,
            "original_name": file_name,
            "code": best_code or "---",
            "bom_type": bom_type or "BOM 1",
            "new_filename": target_name,
            "confidence": round(conf * 100, 1),
            "status": status,
            "candidates_count": len(candidates),
        }

        session_data["files"].append({
            "new_filename": target_name,
            "original_name": file_name,
            "code": best_code,
            "bom_type": bom_type or "BOM 1",
            "confidence": conf,
            "status": status,
            "file_bytes": file_bytes,
        })

        return JSONResponse(result)

    except Exception as e:
        print(f"[WebScan] Single error {file_name}: {e}")
        return JSONResponse({
            "session_id": session_id,
            "original_name": file_name,
            "code": "---",
            "bom_type": "Không rõ",
            "new_filename": file_name,
            "confidence": 0.0,
            "status": f"Lỗi OCR: {str(e)[:50]}",
            "candidates_count": 0,
        })
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
    """Serves the built standalone Windows .exe or ZIP distribution if available."""
    import shutil
    dist_dir = os.path.join(os.path.dirname(BASE_DIR), "dist")
    exe_folder = os.path.join(dist_dir, "AI_OCR_Image_Renamer")
    exe_file = os.path.join(exe_folder, "AI_OCR_Image_Renamer.exe")
    zip_path = os.path.join(dist_dir, "AI_OCR_Image_Renamer_Windows.zip")

    # 1. Check if zipped bundle exists
    if os.path.exists(zip_path):
        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename="AI_OCR_Image_Renamer_Windows.zip",
        )

    # 2. Check if folder exists and zip it on the fly
    if os.path.exists(exe_file):
        try:
            shutil.make_archive(zip_path.replace(".zip", ""), "zip", exe_folder)
            return FileResponse(
                zip_path,
                media_type="application/zip",
                filename="AI_OCR_Image_Renamer_Windows.zip",
            )
        except Exception:
            return FileResponse(
                exe_file,
                media_type="application/octet-stream",
                filename="AI_OCR_Image_Renamer.exe",
            )

    # 3. If running in Cloud container (Railway), return HTML download guidance
    guide_html = """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <title>Hướng Dẫn Tải Bản Cài Đặt Desktop</title>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@600;700&family=Plus+Jakarta+Sans:wght@400;600&display=swap" rel="stylesheet">
        <style>
            body { font-family: 'Plus Jakarta Sans', sans-serif; background: #090d16; color: #f8fafc; text-align: center; padding: 60px 20px; }
            .card { max-width: 600px; margin: 0 auto; background: rgba(15,23,42,0.8); border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; padding: 40px; }
            h1 { font-family: 'Outfit'; color: #818cf8; margin-bottom: 16px; }
            p { color: #94a3b8; line-height: 1.6; margin-bottom: 24px; }
            .code-box { background: #020617; border: 1px solid #1e293b; border-radius: 8px; padding: 14px; color: #38bdf8; font-family: Consolas, monospace; font-size: 15px; margin-bottom: 24px; text-align: left; }
            .btn { display: inline-block; background: #6366f1; color: #fff; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🚀 Bản Desktop Windows (.EXE)</h1>
            <p>Để tạo file <strong>.exe</strong> chạy trực tiếp trên máy tính cá nhân của bạn, hãy mở PowerShell tại thư mục dự án và chạy lệnh:</p>
            <div class="code-box">.\\venv\\Scripts\\python.exe build_exe.py</div>
            <p>Sau khi đóng gói xong, ứng dụng <strong>AI_OCR_Image_Renamer.exe</strong> sẽ nằm trong thư mục <code>dist/</code> để bạn sử dụng offline!</p>
            <a href="/" class="btn">⬅️ Quay Lại Trang Chủ</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=guide_html)
