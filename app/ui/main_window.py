"""
Main GUI window for AI OCR Batch Image Renamer built with CustomTkinter.
"""

import os
import time
import threading
from typing import List, Optional
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from app.config import AppConfig
from app.models import ImageTask, ProcessStatus, RenameRecord
from app.image_processor import ImageProcessor
from app.ocr_engine import OCREngine
from app.filename_extractor import FilenameExtractor
from app.rename_manager import RenameManager
from app.ui.preview_table import PreviewTable
from app.ui.settings_dialog import SettingsDialog
from app.ui.copy_bom_dialog import CopyBomDialog


class MainWindow(ctk.CTk):
    """Main Application Window."""

    def __init__(self):
        super().__init__()

        self.config = AppConfig.load()
        self.tasks: List[ImageTask] = []
        self.current_folder: str = ""
        self.rename_records: List[RenameRecord] = []

        # Threading state
        self._is_processing = False
        self._stop_requested = False
        self._worker_thread: Optional[threading.Thread] = None

        self._init_window()
        self._build_ui()

    def _init_window(self):
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.title("AI OCR Batch Image Renamer - Tự Động Đổi Tên Ảnh Bằng OCR Offline")
        self.geometry("1200x800")
        self.minsize(950, 650)

    def _build_ui(self):
        self.grid_rowconfigure(3, weight=1)  # Preview table row expands
        self.grid_columnconfigure(0, weight=1)

        # 1. Header Bar
        self._build_header()

        # 2. Folder Selection Bar
        self._build_folder_bar()

        # 3. Extraction Rule / Filter Bar
        self._build_filter_bar()

        # 4. Center Preview Table & Stats
        self._build_center_table()

        # 5. Bottom Action & Progress Bar
        self._build_bottom_bar()

    def _build_header(self):
        header = ctk.CTkFrame(self, height=55, corner_radius=0, fg_color="#0f172a")
        header.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header.grid_columnconfigure(1, weight=1)

        lbl_logo = ctk.CTkLabel(
            header,
            text="🏷️ AI OCR RENAMER",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#38bdf8",
        )
        lbl_logo.grid(row=0, column=0, padx=(20, 10), pady=12, sticky="w")

        lbl_sub = ctk.CTkLabel(
            header,
            text="Local PaddleOCR • Đọc mã & Đổi tên hàng loạt • An toàn chống trùng lặp",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#94a3b8",
        )
        lbl_sub.grid(row=0, column=1, padx=5, pady=12, sticky="w")

        # Dark/Light switch
        self.switch_theme = ctk.CTkSwitch(
            header,
            text="Sáng / Tối",
            command=self._toggle_theme,
            font=ctk.CTkFont(family="Segoe UI", size=12),
        )
        self.switch_theme.select()
        self.switch_theme.grid(row=0, column=2, padx=20, pady=12, sticky="e")

    def _build_folder_bar(self):
        f_bar = ctk.CTkFrame(self, corner_radius=8)
        f_bar.grid(row=1, column=0, sticky="ew", padx=15, pady=(10, 5))
        f_bar.grid_columnconfigure(1, weight=1)

        btn_browse = ctk.CTkButton(
            f_bar,
            text="📁 Chọn Thư Mục Ảnh",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self._browse_folder,
            width=170,
            height=36,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
        )
        btn_browse.grid(row=0, column=0, padx=(10, 8), pady=8)

        self.ent_folder = ctk.CTkEntry(
            f_bar,
            placeholder_text="Đường dẫn thư mục chứa ảnh (.jpg, .jpeg, .png, .webp)...",
            height=36,
            font=ctk.CTkFont(family="Segoe UI", size=12),
        )
        self.ent_folder.grid(row=0, column=1, sticky="ew", padx=5, pady=8)
        self.ent_folder.bind("<Return>", lambda e: self._load_folder_images(self.ent_folder.get().strip()))

        btn_refresh = ctk.CTkButton(
            f_bar,
            text="🔄 Quét Lại",
            width=90,
            height=36,
            fg_color="#475569",
            hover_color="#334155",
            command=lambda: self._load_folder_images(self.ent_folder.get().strip()),
        )
        btn_refresh.grid(row=0, column=2, padx=(5, 10), pady=8)

    def _build_filter_bar(self):
        f_filter = ctk.CTkFrame(self, corner_radius=8)
        f_filter.grid(row=2, column=0, sticky="ew", padx=15, pady=5)
        f_filter.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(
            f_filter,
            text="Mẫu nhận diện:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
        ).grid(row=0, column=0, padx=(12, 5), pady=8)

        self.var_preset = ctk.StringVar(value="Số BV CHENKAI (8058991CTIM21-04)")
        self.opt_preset = ctk.CTkOptionMenu(
            f_filter,
            values=[
                "Số BV CHENKAI (8058991CTIM21-04)",
                "Mã Bản Vẽ / BOM ([A-Za-z0-9-]+)",
                "Mã Khách Hàng (Số 8-12 chữ số)",
                "Mã Tập Đoàn / Part No ([A-Z0-9]+)",
                "Chữ và Số ([A-Za-z0-9]+)",
                "Chỉ lấy số (\\d+)",
                "Tùy chỉnh (Custom Regex)",
            ],
            variable=self.var_preset,
            command=self._on_preset_changed,
            width=260,
            height=32,
        )
        self.opt_preset.grid(row=0, column=1, padx=5, pady=8)

        ctk.CTkLabel(f_filter, text="Regex:").grid(row=0, column=2, padx=(10, 5), pady=8)
        self.ent_regex = ctk.CTkEntry(
            f_filter,
            height=32,
            font=ctk.CTkFont(family="Consolas", size=12),
        )
        self.ent_regex.insert(0, r"[0-9A-Za-z]{6,15}-[0-9]{2}")
        self.ent_regex.grid(row=0, column=3, sticky="ew", padx=5, pady=8)

        # Min/Max length
        ctk.CTkLabel(f_filter, text="Độ dài:").grid(row=0, column=4, padx=(10, 2), pady=8)
        self.ent_min_len = ctk.CTkEntry(f_filter, width=45, height=32)
        self.ent_min_len.insert(0, "10")
        self.ent_min_len.grid(row=0, column=5, padx=2, pady=8)

        ctk.CTkLabel(f_filter, text="-").grid(row=0, column=6, padx=1, pady=8)
        self.ent_max_len = ctk.CTkEntry(f_filter, width=45, height=32)
        self.ent_max_len.insert(0, "25")
        self.ent_max_len.grid(row=0, column=7, padx=2, pady=8)

        # Settings button
        btn_settings = ctk.CTkButton(
            f_filter,
            text="⚙️ Cài Đặt Nâng Cao",
            width=140,
            height=32,
            fg_color="#64748b",
            hover_color="#475569",
            command=self._open_settings,
        )
        btn_settings.grid(row=0, column=8, padx=(10, 12), pady=8)

    def _build_center_table(self):
        center_frame = ctk.CTkFrame(self, corner_radius=8)
        center_frame.grid(row=3, column=0, sticky="nsew", padx=15, pady=5)
        center_frame.grid_rowconfigure(1, weight=1)
        center_frame.grid_columnconfigure(0, weight=1)

        # Stats Counter Bar
        stats_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
        stats_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(6, 4))

        self.lbl_stats_total = self._create_badge(stats_frame, "Tổng: 0", "#334155")
        self.lbl_stats_total.pack(side="left", padx=4)

        self.lbl_stats_bom1 = self._create_badge(stats_frame, "BOM 1: 0", "#0284c7")
        self.lbl_stats_bom1.pack(side="left", padx=4)

        self.lbl_stats_bom2 = self._create_badge(stats_frame, "BOM 2: 0", "#7c3aed")
        self.lbl_stats_bom2.pack(side="left", padx=4)

        self.lbl_stats_success = self._create_badge(stats_frame, "Nhận diện: 0", "#065f46")
        self.lbl_stats_success.pack(side="left", padx=4)

        self.lbl_stats_failed = self._create_badge(stats_frame, "Không tìm thấy: 0", "#831843")
        self.lbl_stats_failed.pack(side="left", padx=4)

        self.lbl_stats_renamed = self._create_badge(stats_frame, "Đã đổi tên: 0", "#1e3a8a")
        self.lbl_stats_renamed.pack(side="left", padx=4)

        lbl_hint = ctk.CTkLabel(
            stats_frame,
            text="💡 Nhấp đúp để xem ảnh & Bounding Box | Chuột phải để chọn ứng viên hoặc sửa tay",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#94a3b8",
        )
        lbl_hint.pack(side="right", padx=5)

        # Preview Table Component
        self.table = PreviewTable(
            center_frame,
            on_task_modified=self._on_task_modified,
            corner_radius=6,
        )
        self.table.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

    def _create_badge(self, parent, text: str, bg_color: str) -> ctk.CTkLabel:
        return ctk.CTkLabel(
            parent,
            text=text,
            corner_radius=6,
            fg_color=bg_color,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            padx=10,
            pady=3,
        )

    def _build_bottom_bar(self):
        bottom_frame = ctk.CTkFrame(self, corner_radius=8)
        bottom_frame.grid(row=4, column=0, sticky="ew", padx=15, pady=(5, 15))
        bottom_frame.grid_columnconfigure(0, weight=1)

        # Progress row
        prog_row = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        prog_row.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(8, 4))
        prog_row.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(prog_row, height=12, corner_radius=6)
        self.progress_bar.set(0.0)
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=(0, 10), pady=5)

        self.lbl_prog_percent = ctk.CTkLabel(
            prog_row,
            text="0%",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            width=50,
        )
        self.lbl_prog_percent.grid(row=0, column=1, sticky="e")

        # Status Label & Action Buttons
        act_row = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        act_row.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 8))
        act_row.grid_columnconfigure(0, weight=1)

        self.lbl_status = ctk.CTkLabel(
            act_row,
            text="Sẵn sàng. Vui lòng chọn thư mục chứa ảnh.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#94a3b8",
            anchor="w",
        )
        self.lbl_status.grid(row=0, column=0, sticky="w", padx=5)

        # Action Buttons
        self.btn_scan = ctk.CTkButton(
            act_row,
            text="🚀 Bắt Đầu Quét OCR",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            height=38,
            width=170,
            command=self._start_ocr_scan,
        )
        self.btn_scan.grid(row=0, column=1, padx=5)

        self.btn_stop = ctk.CTkButton(
            act_row,
            text="⏹️ Dừng",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#ef4444",
            hover_color="#dc2626",
            height=38,
            width=90,
            state="disabled",
            command=self._stop_ocr_scan,
        )
        self.btn_stop.grid(row=0, column=2, padx=5)

        self.btn_rename = ctk.CTkButton(
            act_row,
            text="✏️ Thực Hiện Đổi Tên (Rename)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            height=38,
            width=200,
            command=self._execute_rename,
        )
        self.btn_rename.grid(row=0, column=3, padx=5)

        self.btn_copy_bom = ctk.CTkButton(
            act_row,
            text="📋 Sao Chép BOM",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#7c3aed",
            hover_color="#6d28d9",
            height=38,
            width=140,
            command=self._open_copy_bom_dialog,
        )
        self.btn_copy_bom.grid(row=0, column=4, padx=5)

        self.btn_csv = ctk.CTkButton(
            act_row,
            text="📊 Xuất CSV",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#475569",
            hover_color="#334155",
            height=38,
            width=110,
            command=self._export_csv,
        )
        self.btn_csv.grid(row=0, column=5, padx=5)

        self.btn_clear = ctk.CTkButton(
            act_row,
            text="🗑️ Xóa",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#334155",
            hover_color="#1e293b",
            height=38,
            width=70,
            command=self._clear_all,
        )
        self.btn_clear.grid(row=0, column=6, padx=(5, 0))

    # --- Event Handlers & Core Methods ---

    def _toggle_theme(self):
        if self.switch_theme.get():
            ctk.set_appearance_mode("Dark")
        else:
            ctk.set_appearance_mode("Light")

    def _browse_folder(self):
        folder = filedialog.askdirectory(title="Chọn thư mục chứa hình ảnh")
        if folder:
            self.ent_folder.delete(0, "end")
            self.ent_folder.insert(0, folder)
            self._load_folder_images(folder)

    def _load_folder_images(self, folder: str):
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning("Cảnh báo", "Thư mục không tồn tại. Vui lòng kiểm tra lại.")
            return

        self.current_folder = folder
        self.tasks.clear()
        valid_exts = tuple(self.config.supported_extensions)

        try:
            entries = os.listdir(folder)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể đọc thư mục: {e}")
            return

        for idx, filename in enumerate(entries):
            file_path = os.path.join(folder, filename)
            if not os.path.isfile(file_path):
                continue
            ext = os.path.splitext(filename)[1].lower()
            if ext in valid_exts:
                task = ImageTask(
                    task_id=f"task_{idx}_{filename}",
                    file_path=file_path,
                    original_name=filename,
                    extension=ext,
                    file_size_bytes=os.path.getsize(file_path),
                    new_filename=filename,
                    status=ProcessStatus.PENDING,
                )
                self.tasks.append(task)

        self.table.set_tasks(self.tasks)
        self._update_stats()
        self.lbl_status.configure(
            text=f"Đã tìm thấy {len(self.tasks)} tệp hình ảnh hợp lệ trong thư mục."
        )

    def _on_preset_changed(self, choice: str):
        if "Số BV CHENKAI" in choice:
            self.ent_regex.delete(0, "end")
            self.ent_regex.insert(0, r"[0-9A-Za-z]{6,15}-[0-9]{2}")
            self.ent_min_len.delete(0, "end")
            self.ent_min_len.insert(0, "10")
            self.ent_max_len.delete(0, "end")
            self.ent_max_len.insert(0, "25")
        elif "Mã Bản Vẽ / BOM" in choice:
            self.ent_regex.delete(0, "end")
            self.ent_regex.insert(0, r"[0-9A-Za-z]{4,15}(?:-[0-9A-Za-z]+)?")
            self.ent_min_len.delete(0, "end")
            self.ent_min_len.insert(0, "6")
            self.ent_max_len.delete(0, "end")
            self.ent_max_len.insert(0, "25")
        elif "Mã Khách Hàng" in choice:
            self.ent_regex.delete(0, "end")
            self.ent_regex.insert(0, r"\b\d{8,12}\b")
            self.ent_min_len.delete(0, "end")
            self.ent_min_len.insert(0, "8")
            self.ent_max_len.delete(0, "end")
            self.ent_max_len.insert(0, "12")
        elif "Mã Tập Đoàn" in choice:
            self.ent_regex.delete(0, "end")
            self.ent_regex.insert(0, r"\b\d{4}[A-Za-z]{4,6}\d{2}\b")
            self.ent_min_len.delete(0, "end")
            self.ent_min_len.insert(0, "8")
            self.ent_max_len.delete(0, "end")
            self.ent_max_len.insert(0, "15")
        elif "Chữ và Số" in choice:
            self.ent_regex.delete(0, "end")
            self.ent_regex.insert(0, r"[A-Za-z0-9]{4,25}")
            self.ent_min_len.delete(0, "end")
            self.ent_min_len.insert(0, "4")
            self.ent_max_len.delete(0, "end")
            self.ent_max_len.insert(0, "30")
        elif "Chỉ lấy số" in choice:
            self.ent_regex.delete(0, "end")
            self.ent_regex.insert(0, r"\b\d{4,12}\b")
            self.ent_min_len.delete(0, "end")
            self.ent_min_len.insert(0, "4")
            self.ent_max_len.delete(0, "end")
            self.ent_max_len.insert(0, "12")

    def _sync_config_from_ui(self):
        self.config.regex_pattern = self.ent_regex.get().strip()
        try:
            self.config.min_length = int(self.ent_min_len.get().strip())
        except ValueError:
            self.config.min_length = 4
        try:
            self.config.max_length = int(self.ent_max_len.get().strip())
        except ValueError:
            self.config.max_length = 30

    def _open_settings(self):
        self._sync_config_from_ui()
        SettingsDialog(self, self.config, on_save_callback=self._on_settings_saved)

    def _on_settings_saved(self, new_config: AppConfig):
        self.config = new_config
        self.ent_regex.delete(0, "end")
        self.ent_regex.insert(0, self.config.regex_pattern)
        self.ent_min_len.delete(0, "end")
        self.ent_min_len.insert(0, str(self.config.min_length))
        self.ent_max_len.delete(0, "end")
        self.ent_max_len.insert(0, str(self.config.max_length))
        # Re-resolve filenames
        RenameManager.resolve_filename_conflicts(self.tasks, self.config)
        self.table.refresh()
        self._update_stats()

    def _on_task_modified(self, task: ImageTask):
        RenameManager.resolve_filename_conflicts(self.tasks, self.config)
        self._update_stats()

    def _update_stats(self):
        total = len(self.tasks)
        success = sum(1 for t in self.tasks if t.is_successful)
        failed = sum(1 for t in self.tasks if t.status in [ProcessStatus.NO_CANDIDATE, ProcessStatus.FAILED])
        renamed = sum(1 for t in self.tasks if t.status == ProcessStatus.RENAMED)
        bom1 = sum(1 for t in self.tasks if "1" in t.bom_type or "BOM 1" in t.bom_type)
        bom2 = sum(1 for t in self.tasks if "2" in t.bom_type or "BOM 2" in t.bom_type)

        self.lbl_stats_total.configure(text=f"Tổng: {total}")
        self.lbl_stats_bom1.configure(text=f"BOM 1: {bom1}")
        self.lbl_stats_bom2.configure(text=f"BOM 2: {bom2}")
        self.lbl_stats_success.configure(text=f"Nhận diện: {success}")
        self.lbl_stats_failed.configure(text=f"Không tìm thấy: {failed}")
        self.lbl_stats_renamed.configure(text=f"Đã đổi tên: {renamed}")

    # --- OCR Background Processing ---

    def _start_ocr_scan(self):
        if not self.tasks:
            messagebox.showinfo("Thông báo", "Vui lòng chọn thư mục có hình ảnh trước.")
            return

        if self._is_processing:
            return

        self._sync_config_from_ui()
        self._is_processing = True
        self._stop_requested = False

        self.btn_scan.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.btn_rename.configure(state="disabled")
        self.progress_bar.set(0.0)

        self._worker_thread = threading.Thread(target=self._ocr_worker_loop, daemon=True)
        self._worker_thread.start()

    def _stop_ocr_scan(self):
        if self._is_processing:
            self._stop_requested = True
            self.lbl_status.configure(text="Đang dừng tiến trình quét...")
            self.btn_stop.configure(state="disabled")

    def _ocr_worker_loop(self):
        total = len(self.tasks)
        extractor = FilenameExtractor(self.config)
        start_time = time.time()

        try:
            ocr_engine = OCREngine.get_instance(
                lang=self.config.ocr_language,
                use_angle_cls=self.config.use_angle_cls,
                use_gpu=self.config.use_gpu,
            )
        except Exception as e:
            self.after(0, lambda err=e: messagebox.showerror("Lỗi OCR Engine", str(err)))
            self.after(0, self._finish_ocr_scan)
            return

        for idx, task in enumerate(self.tasks):
            if self._stop_requested:
                break

            task.status = ProcessStatus.PROCESSING
            self.after(0, lambda t=task: self.table.update_task_row(t))

            # Progress info
            progress_ratio = (idx + 1) / float(total)
            elapsed = max(0.1, time.time() - start_time)
            fps = (idx + 1) / elapsed
            status_text = f"Đang quét ({idx + 1}/{total}) - {task.original_name} ({fps:.1f} ảnh/giây)"

            self.after(0, lambda pr=progress_ratio, st=status_text: self._update_progress_ui(pr, st))

            try:
                # 1. Load image (Unicode safe)
                img = ImageProcessor.load_image_unicode(task.file_path)
                if img is None:
                    task.status = ProcessStatus.FAILED
                    task.error_message = "Không thể mở file ảnh"
                    self.after(0, lambda t=task: self.table.update_task_row(t))
                    continue

                # 2. Preprocess
                processed_img = ImageProcessor.preprocess_for_ocr(img, self.config)

                # 3. PaddleOCR inference
                ocr_results = ocr_engine.recognize(processed_img)
                task.all_detected_text = [text for _, text, _ in ocr_results]

                # 4. Extract candidates & Classify BOM Type (BOM 1 / BOM 2)
                candidates = extractor.extract_candidates(ocr_results)
                task.candidates = candidates
                task.bom_type = extractor.detect_bom_type(ocr_results)

                if candidates:
                    task.selected_candidate_index = 0
                    task.status = ProcessStatus.SUCCESS
                else:
                    task.status = ProcessStatus.NO_CANDIDATE

            except Exception as e:
                task.status = ProcessStatus.FAILED
                task.error_message = str(e)
                print(f"[Worker] Error processing {task.original_name}: {e}")

            # Update row in UI
            self.after(0, lambda t=task: self.table.update_task_row(t))

        # Complete pass
        self.after(0, self._finish_ocr_scan)

    def _update_progress_ui(self, ratio: float, status_text: str):
        self.progress_bar.set(ratio)
        self.lbl_prog_percent.configure(text=f"{ratio:.0%}")
        self.lbl_status.configure(text=status_text)
        self._update_stats()

    def _finish_ocr_scan(self):
        self._is_processing = False
        self.btn_scan.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.btn_rename.configure(state="normal")

        # Compute preview filenames with conflict detection
        RenameManager.resolve_filename_conflicts(self.tasks, self.config)
        self.table.refresh()
        self._update_stats()

        success_cnt = sum(1 for t in self.tasks if t.is_successful)
        total = len(self.tasks)
        self.lbl_status.configure(
            text=f"Quét OCR hoàn tất! Nhận diện thành công {success_cnt}/{total} ảnh. Hãy kiểm tra trước khi bấm 'Đổi Tên'."
        )

    # --- Renaming Execution ---

    def _execute_rename(self):
        if not self.tasks:
            messagebox.showinfo("Thông báo", "Không có file nào để đổi tên.")
            return

        valid_count = sum(1 for t in self.tasks if t.is_successful)
        if valid_count == 0:
            messagebox.showwarning(
                "Cảnh báo",
                "Chưa có file nào nhận diện được mã hợp lệ để đổi tên.\nHãy chạy quét OCR trước hoặc nhập sửa mã thủ công.",
            )
            return

        confirm = messagebox.askyesno(
            "Xác nhận đổi tên",
            f"Bạn có chắc chắn muốn đổi tên {valid_count} file ảnh theo kết quả OCR không?\n\n"
            f"Lưu ý: Các file trùng tên sẽ tự động được thêm hậu tố _1, _2...",
            parent=self,
        )
        if not confirm:
            return

        # Execute
        success, failed, records = RenameManager.execute_renames(self.tasks, self.config)
        self.rename_records = records

        self.table.refresh()
        self._update_stats()

        messagebox.showinfo(
            "Kết quả đổi tên",
            f"Hoàn thành đổi tên:\n- Thành công: {success} file\n- Thất bại / Bỏ qua: {failed} file",
            parent=self,
        )
        self.lbl_status.configure(text=f"Đã đổi tên thành công {success} file.")

    # --- BOM Copy & Export ---

    def _open_copy_bom_dialog(self):
        if not self.tasks:
            messagebox.showinfo("Thông báo", "Chưa có danh sách file để sao chép.", parent=self)
            return
        CopyBomDialog(self, self.tasks)

    # --- CSV Export ---

    def _export_csv(self):
        if not self.tasks:
            messagebox.showinfo("Thông báo", "Chưa có dữ liệu để xuất CSV.", parent=self)
            return

        default_name = f"ocr_rename_log_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        file_path = filedialog.asksaveasfilename(
            title="Lưu Báo Cáo CSV",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV Files (*.csv)", "*.csv"), ("All Files (*.*)", "*.*")],
        )
        if not file_path:
            return

        # Prepare records from current tasks if not already executed
        records = []
        for t in self.tasks:
            records.append(
                RenameRecord(
                    original_filename=t.original_name,
                    detected_text=" | ".join(t.all_detected_text),
                    extracted_number=t.current_code,
                    bom_type=t.bom_type,
                    new_filename=t.new_filename or t.original_name,
                    confidence=t.current_confidence,
                    status=t.status.value,
                    error_message=t.error_message,
                )
            )

        if RenameManager.export_csv(records, file_path):
            messagebox.showinfo("Thành công", f"Đã xuất báo cáo CSV thành công tại:\n{file_path}", parent=self)
        else:
            messagebox.showerror("Lỗi", "Không thể xuất file CSV.", parent=self)

    def _clear_all(self):
        if self._is_processing:
            messagebox.showwarning("Cảnh báo", "Tiến trình OCR đang chạy. Vui lòng dừng trước.", parent=self)
            return

        self.tasks.clear()
        self.table.set_tasks([])
        self.progress_bar.set(0.0)
        self.lbl_prog_percent.configure(text="0%")
        self.lbl_status.configure(text="Đã xóa danh sách.")
        self._update_stats()
