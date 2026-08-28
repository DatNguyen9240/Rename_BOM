"""
Advanced settings dialog window for AI OCR Batch Image Renamer.
"""

import customtkinter as ctk
from typing import Callable, Optional
from app.config import AppConfig


class SettingsDialog(ctk.CTkToplevel):
    """Configuration dialog for fine-tuning OCR, preprocessing, and renaming rules."""

    def __init__(self, parent, config: AppConfig, on_save_callback: Optional[Callable[[AppConfig], None]] = None):
        super().__init__(parent)
        self.config = config
        self.on_save_callback = on_save_callback

        self.title("Cài Đặt Nâng Cao - AI OCR Renamer")
        self.geometry("680x720")
        self.minsize(580, 600)

        self.after(100, self.lift)
        self.after(150, self.focus_force)

        self._build_ui()
        self._load_values()

    def _build_ui(self):
        # Scrollable container
        self.scroll_frame = ctk.CTkScrollableFrame(self, corner_radius=10)
        self.scroll_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # Title
        lbl_title = ctk.CTkLabel(
            self.scroll_frame,
            text="⚙️ Tùy Chỉnh Cấu Hình AI OCR & Tiền Xử Lý Ảnh",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            anchor="w"
        )
        lbl_title.pack(fill="x", padx=10, pady=(5, 15))

        # --- Section 1: PaddleOCR Engine Settings ---
        sec1 = self._create_section("1. Cấu hình PaddleOCR Engine")

        # OCR Language
        f_lang = ctk.CTkFrame(sec1, fg_color="transparent")
        f_lang.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(f_lang, text="Ngôn ngữ OCR:", width=180, anchor="w").pack(side="left")
        self.var_lang = ctk.StringVar(value=self.config.ocr_language)
        self.opt_lang = ctk.CTkOptionMenu(
            f_lang,
            values=["en", "ch", "vi", "latin"],
            variable=self.var_lang,
            width=150
        )
        self.opt_lang.pack(side="left")

        # Angle Classification
        self.var_angle = ctk.BooleanVar(value=self.config.use_angle_cls)
        self.chk_angle = ctk.CTkCheckBox(
            sec1,
            text="Tự động nhận diện hướng xoay chữ (use_angle_cls)",
            variable=self.var_angle
        )
        self.chk_angle.pack(fill="x", padx=10, pady=5)

        # Confidence Threshold Slider
        f_conf = ctk.CTkFrame(sec1, fg_color="transparent")
        f_conf.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(f_conf, text="Ngưỡng tin cậy (Confidence):", width=180, anchor="w").pack(side="left")
        self.var_conf = ctk.DoubleVar(value=self.config.confidence_threshold)
        self.slider_conf = ctk.CTkSlider(
            f_conf,
            from_=0.10,
            to=0.99,
            number_of_steps=89,
            variable=self.var_conf,
            command=self._update_conf_label
        )
        self.slider_conf.pack(side="left", fill="x", expand=True, padx=5)
        self.lbl_conf_val = ctk.CTkLabel(f_conf, text=f"{self.config.confidence_threshold:.0%}", width=50)
        self.lbl_conf_val.pack(side="left")

        # --- Section 2: Image Preprocessing Pipeline ---
        sec2 = self._create_section("2. Tiền Xử Lý Ảnh (Image Preprocessing)")

        self.var_preproc = ctk.BooleanVar(value=self.config.enable_preprocessing)
        self.chk_preproc = ctk.CTkCheckBox(
            sec2,
            text="Kích hoạt bộ lọc tiền xử lý ảnh (Tăng độ nét & tương phản)",
            variable=self.var_preproc,
            font=ctk.CTkFont(weight="bold")
        )
        self.chk_preproc.pack(fill="x", padx=10, pady=5)

        self.var_exif = ctk.BooleanVar(value=self.config.auto_rotate_exif)
        self.chk_exif = ctk.CTkCheckBox(sec2, text="Tự động xoay ảnh theo EXIF Orientation", variable=self.var_exif)
        self.chk_exif.pack(fill="x", padx=10, pady=3)

        self.var_gray = ctk.BooleanVar(value=self.config.to_grayscale)
        self.chk_gray = ctk.CTkCheckBox(sec2, text="Chuyển sang ảnh Grayscale", variable=self.var_gray)
        self.chk_gray.pack(fill="x", padx=10, pady=3)

        self.var_clahe = ctk.BooleanVar(value=self.config.enhance_contrast_clahe)
        self.chk_clahe = ctk.CTkCheckBox(sec2, text="Cân bằng sáng cục bộ (CLAHE Contrast Enhancement)", variable=self.var_clahe)
        self.chk_clahe.pack(fill="x", padx=10, pady=3)

        self.var_sharpen = ctk.BooleanVar(value=self.config.sharpen_image)
        self.chk_sharpen = ctk.CTkCheckBox(sec2, text="Làm sắc nét viền chữ (Sharpen / Unsharp Mask)", variable=self.var_sharpen)
        self.chk_sharpen.pack(fill="x", padx=10, pady=3)

        self.var_adaptive = ctk.BooleanVar(value=self.config.adaptive_threshold)
        self.chk_adaptive = ctk.CTkCheckBox(sec2, text="Nhị phân hóa thích nghi (Adaptive Threshold - Dành cho nền phức tạp)", variable=self.var_adaptive)
        self.chk_adaptive.pack(fill="x", padx=10, pady=3)

        # Max dimension
        f_dim = ctk.CTkFrame(sec2, fg_color="transparent")
        f_dim.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(f_dim, text="Kích thước ảnh tối đa (px):", width=180, anchor="w").pack(side="left")
        self.ent_dim = ctk.CTkEntry(f_dim, width=120)
        self.ent_dim.pack(side="left")

        # --- Section 3: Smart Disambiguation / OCR Correction ---
        sec3 = self._create_section("3. Sửa Lỗi Nhầm Lẫn Ký Tự OCR (Disambiguation)")

        self.var_disam = ctk.BooleanVar(value=self.config.enable_disambiguation)
        self.chk_disam = ctk.CTkCheckBox(
            sec3,
            text="Bật cơ chế tự sửa ký tự nhầm lẫn khi trong chuỗi số/mã",
            variable=self.var_disam,
            font=ctk.CTkFont(weight="bold")
        )
        self.chk_disam.pack(fill="x", padx=10, pady=5)

        self.var_corr_o = ctk.BooleanVar(value=self.config.correct_o_to_zero)
        ctk.CTkCheckBox(sec3, text="Sửa ký tự 'O' / 'o' → '0' (Số Không)", variable=self.var_corr_o).pack(fill="x", padx=25, pady=2)

        self.var_corr_i = ctk.BooleanVar(value=self.config.correct_i_to_one)
        ctk.CTkCheckBox(sec3, text="Sửa ký tự 'I' / 'l' / '|' → '1' (Số Một)", variable=self.var_corr_i).pack(fill="x", padx=25, pady=2)

        self.var_corr_s = ctk.BooleanVar(value=self.config.correct_s_to_five)
        ctk.CTkCheckBox(sec3, text="Sửa ký tự 'S' / 's' → '5' (Số Năm)", variable=self.var_corr_s).pack(fill="x", padx=25, pady=2)

        self.var_corr_b = ctk.BooleanVar(value=self.config.correct_b_to_eight)
        ctk.CTkCheckBox(sec3, text="Sửa ký tự 'B' → '8' (Số Tám)", variable=self.var_corr_b).pack(fill="x", padx=25, pady=2)

        self.var_corr_z = ctk.BooleanVar(value=self.config.correct_z_to_two)
        ctk.CTkCheckBox(sec3, text="Sửa ký tự 'Z' / 'z' → '2' (Số Hai)", variable=self.var_corr_z).pack(fill="x", padx=25, pady=2)

        # --- Section 4: Renaming Format & Suffix ---
        sec4 = self._create_section("4. Định Dạng Tên File Mới")

        f_pre = ctk.CTkFrame(sec4, fg_color="transparent")
        f_pre.pack(fill="x", padx=10, pady=3)
        ctk.CTkLabel(f_pre, text="Tiền tố (Prefix):", width=140, anchor="w").pack(side="left")
        self.ent_prefix = ctk.CTkEntry(f_pre, width=160, placeholder_text="VD: IMG_ hoặc ITEM_")
        self.ent_prefix.pack(side="left")

        f_suf = ctk.CTkFrame(sec4, fg_color="transparent")
        f_suf.pack(fill="x", padx=10, pady=3)
        ctk.CTkLabel(f_suf, text="Hậu tố (Suffix):", width=140, anchor="w").pack(side="left")
        self.ent_suffix = ctk.CTkEntry(f_suf, width=160, placeholder_text="VD: _DONE hoặc _OCR")
        self.ent_suffix.pack(side="left")

        f_case = ctk.CTkFrame(sec4, fg_color="transparent")
        f_case.pack(fill="x", padx=10, pady=3)
        ctk.CTkLabel(f_case, text="Định dạng chữ:", width=140, anchor="w").pack(side="left")
        self.var_case = ctk.StringVar(value=self.config.case_format)
        self.opt_case = ctk.CTkOptionMenu(
            f_case,
            values=["AS_IS", "UPPER", "LOWER"],
            variable=self.var_case,
            width=160
        )
        self.opt_case.pack(side="left")

        # Bottom Button Bar
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.pack(fill="x", padx=15, pady=(0, 15))

        btn_save = ctk.CTkButton(
            btn_bar,
            text="💾 Lưu Cấu Hình",
            fg_color="#10b981",
            hover_color="#059669",
            command=self._on_save,
            width=140,
            height=36,
            font=ctk.CTkFont(weight="bold")
        )
        btn_save.pack(side="right", padx=5)

        btn_cancel = ctk.CTkButton(
            btn_bar,
            text="Hủy",
            fg_color="#64748b",
            hover_color="#475569",
            command=self.destroy,
            width=90,
            height=36
        )
        btn_cancel.pack(side="right", padx=5)

    def _create_section(self, title: str) -> ctk.CTkFrame:
        sec = ctk.CTkFrame(self.scroll_frame, corner_radius=8)
        sec.pack(fill="x", padx=5, pady=8)
        lbl = ctk.CTkLabel(
            sec,
            text=title,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            anchor="w"
        )
        lbl.pack(fill="x", padx=10, pady=(8, 4))
        return sec

    def _update_conf_label(self, val):
        self.lbl_conf_val.configure(text=f"{val:.0%}")

    def _load_values(self):
        self.ent_dim.insert(0, str(self.config.max_dimension))
        self.ent_prefix.insert(0, self.config.prefix)
        self.ent_suffix.insert(0, self.config.suffix)

    def _on_save(self):
        try:
            self.config.ocr_language = self.var_lang.get()
            self.config.use_angle_cls = self.var_angle.get()
            self.config.confidence_threshold = round(self.var_conf.get(), 2)

            self.config.enable_preprocessing = self.var_preproc.get()
            self.config.auto_rotate_exif = self.var_exif.get()
            self.config.to_grayscale = self.var_gray.get()
            self.config.enhance_contrast_clahe = self.var_clahe.get()
            self.config.sharpen_image = self.var_sharpen.get()
            self.config.adaptive_threshold = self.var_adaptive.get()

            try:
                self.config.max_dimension = int(self.ent_dim.get().strip())
            except ValueError:
                self.config.max_dimension = 2000

            self.config.enable_disambiguation = self.var_disam.get()
            self.config.correct_o_to_zero = self.var_corr_o.get()
            self.config.correct_i_to_one = self.var_corr_i.get()
            self.config.correct_s_to_five = self.var_corr_s.get()
            self.config.correct_b_to_eight = self.var_corr_b.get()
            self.config.correct_z_to_two = self.var_corr_z.get()

            self.config.prefix = self.ent_prefix.get().strip()
            self.config.suffix = self.ent_suffix.get().strip()
            self.config.case_format = self.var_case.get()

            self.config.save()

            if self.on_save_callback:
                self.on_save_callback(self.config)

            self.destroy()
        except Exception as e:
            print(f"[SettingsDialog] Error saving: {e}")
