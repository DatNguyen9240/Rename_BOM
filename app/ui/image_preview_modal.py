"""
Modal window for viewing image with highlighted OCR bounding boxes.
"""

import customtkinter as ctk
import cv2
import numpy as np
from PIL import Image, ImageTk
from typing import Optional

from app.models import ImageTask
from app.image_processor import ImageProcessor


class ImagePreviewModal(ctk.CTkToplevel):
    """Displays original image with drawn OCR bounding boxes and extracted candidates."""

    def __init__(self, parent, task: ImageTask):
        super().__init__(parent)
        self.task = task
        self.title(f"Xem ảnh: {task.original_name}")
        self.geometry("900x700")
        self.minsize(600, 500)

        # Bring to front
        self.after(100, self.lift)
        self.after(150, self.focus_force)

        self._build_ui()
        self._load_and_render_image()

    def _build_ui(self):
        # Header Info Frame
        self.header_frame = ctk.CTkFrame(self, corner_radius=8)
        self.header_frame.pack(fill="x", padx=15, pady=(15, 10))

        info_text = (
            f"📁 File: {self.task.original_name}  |  "
            f"🎯 Mã đã chọn: {self.task.current_code or 'Chưa có'}  |  "
            f"📊 Độ tin cậy: {self.task.current_confidence:.1%}  |  "
            f"Trạng thái: {self.task.status.value}"
        )
        self.lbl_info = ctk.CTkLabel(
            self.header_frame,
            text=info_text,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            anchor="w",
        )
        self.lbl_info.pack(fill="x", padx=12, pady=10)

        # Image Container Frame
        self.img_frame = ctk.CTkFrame(self, corner_radius=8)
        self.img_frame.pack(fill="both", expand=True, padx=15, pady=5)

        self.lbl_image = ctk.CTkLabel(self.img_frame, text="Đang tải ảnh...")
        self.lbl_image.pack(fill="both", expand=True, padx=10, pady=10)

        # Candidates details bar
        self.cand_frame = ctk.CTkFrame(self, corner_radius=8)
        self.cand_frame.pack(fill="x", padx=15, pady=(10, 15))

        cand_str = "Danh sách ứng viên phát hiện: " + (
            " | ".join([f"'{c.code}' ({c.confidence:.1%})" for c in self.task.candidates])
            if self.task.candidates
            else "Không có"
        )
        self.lbl_candidates = ctk.CTkLabel(
            self.cand_frame,
            text=cand_str,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            anchor="w",
            wraplength=850,
        )
        self.lbl_candidates.pack(fill="x", padx=12, pady=8)

    def _load_and_render_image(self):
        img_bgr = ImageProcessor.load_image_unicode(self.task.file_path)
        if img_bgr is None:
            self.lbl_image.configure(text=f"Không thể mở ảnh: {self.task.file_path}")
            return

        annotated = img_bgr.copy()

        # Draw bounding boxes
        for cand in self.task.candidates:
            if cand.box_coords:
                try:
                    pts = np.array(cand.box_coords, np.int32).reshape((-1, 1, 2))
                    # Highlight selected candidate in bright green, others in cyan
                    is_selected = (cand.code == self.task.current_code)
                    color = (0, 255, 0) if is_selected else (255, 200, 0)
                    thickness = 3 if is_selected else 2
                    cv2.polylines(annotated, [pts], isClosed=True, color=color, thickness=thickness)

                    # Text label above box
                    x, y = pts[0][0]
                    cv2.putText(
                        annotated,
                        f"{cand.code} ({cand.confidence:.0%})",
                        (max(0, x), max(20, y - 5)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        color,
                        2,
                        cv2.LINE_AA,
                    )
                except Exception as e:
                    print(f"[ImageModal] Draw box error: {e}")

        # Convert to RGB for PIL / Tkinter
        rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]

        # Fit image in display window area (approx 850x450)
        target_w, target_h = 850, 480
        scale = min(target_w / float(w), target_h / float(h), 1.0)
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))

        pil_img = Image.fromarray(rgb).resize((new_w, new_h), Image.Resampling.LANCZOS)
        self.tk_img = ImageTk.PhotoImage(pil_img)
        self.lbl_image.configure(image=self.tk_img, text="")
