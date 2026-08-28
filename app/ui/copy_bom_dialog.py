"""
Copy BOM Dialog modal for filtering, formatting, and copying BOM 1 & BOM 2 codes.
"""

import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
from typing import List
from app.models import ImageTask


class CopyBomDialog(ctk.CTkToplevel):
    """Modern modal dialog allowing users to filter, format, and copy BOM lists."""

    def __init__(self, parent, tasks: List[ImageTask]):
        super().__init__(parent)
        self.tasks = tasks

        self.title("📋 Danh Sách Mã BOM & Phân Loại")
        self.geometry("760x600")
        self.minsize(650, 500)
        self.transient(parent)
        self.grab_set()

        # Center on screen
        self.update_idletasks()
        try:
            x = parent.winfo_x() + (parent.winfo_width() // 2) - 380
            y = parent.winfo_y() + (parent.winfo_height() // 2) - 300
            self.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

        self._build_ui()
        self._update_text_preview()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # 1. Header Frame with Stats
        f_header = ctk.CTkFrame(self, corner_radius=8, fg_color="#1e293b")
        f_header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 10))

        total_valid = [t for t in self.tasks if t.current_code]
        bom1_count = sum(1 for t in total_valid if "1" in t.bom_type)
        bom2_count = sum(1 for t in total_valid if "2" in t.bom_type)
        other_count = len(total_valid) - bom1_count - bom2_count

        lbl_title = ctk.CTkLabel(
            f_header,
            text="📑 BẢNG TRÍCH XUẤT MÃ SẢN PHẨM / BOM",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#f8fafc",
        )
        lbl_title.pack(anchor="w", padx=15, pady=(10, 5))

        f_badges = ctk.CTkFrame(f_header, fg_color="transparent")
        f_badges.pack(anchor="w", padx=15, pady=(0, 10))

        self._create_badge(f_badges, f"Tổng hợp lệ: {len(total_valid)}", "#334155").pack(side="left", padx=(0, 6))
        self._create_badge(f_badges, f"BOM 1: {bom1_count}", "#0284c7").pack(side="left", padx=6)
        self._create_badge(f_badges, f"BOM 2: {bom2_count}", "#7c3aed").pack(side="left", padx=6)
        if other_count > 0:
            self._create_badge(f_badges, f"Khác: {other_count}", "#475569").pack(side="left", padx=6)

        # 2. Control Options Bar
        f_controls = ctk.CTkFrame(self, corner_radius=8)
        f_controls.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 10))

        # Filter Segmented Button
        ctk.CTkLabel(
            f_controls,
            text="Bộ Lọc:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
        ).grid(row=0, column=0, padx=(12, 5), pady=8, sticky="w")

        self.var_filter = ctk.StringVar(value="Tất Cả")
        self.seg_filter = ctk.CTkSegmentedButton(
            f_controls,
            values=["Tất Cả", "Chỉ BOM 1", "Chỉ BOM 2"],
            variable=self.var_filter,
            command=lambda _: self._update_text_preview(),
            height=30,
        )
        self.seg_filter.grid(row=0, column=1, padx=5, pady=8, sticky="w")

        # Format Style Option
        ctk.CTkLabel(
            f_controls,
            text="Định Dạng:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
        ).grid(row=0, column=2, padx=(15, 5), pady=8, sticky="w")

        self.var_format = ctk.StringVar(value="Mã (Loại BOM)")
        self.opt_format = ctk.CTkOptionMenu(
            f_controls,
            values=[
                "Mã (Loại BOM)  [VD: 8018991CTIK64-03 (BOM2)]",
                "Chỉ Mã Số      [VD: 8018991CTIK64-03]",
                "Chi Tiết File  [VD: file.pdf -> 8018991CTIK64-03 (BOM2)]",
            ],
            variable=self.var_format,
            command=lambda _: self._update_text_preview(),
            width=230,
            height=30,
        )
        self.opt_format.grid(row=0, column=3, padx=5, pady=8, sticky="w")

        # Delimiter Option
        ctk.CTkLabel(
            f_controls,
            text="Ngăn Cách:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
        ).grid(row=0, column=4, padx=(15, 5), pady=8, sticky="w")

        self.var_delim = ctk.StringVar(value="Dấu phẩy (, )")
        self.opt_delim = ctk.CTkOptionMenu(
            f_controls,
            values=[
                "Dấu phẩy (, )",
                "Xuống dòng (Enter)",
                "Dấu chấm phẩy (; )",
                "Tab (Cột)",
            ],
            variable=self.var_delim,
            command=lambda _: self._update_text_preview(),
            width=140,
            height=30,
        )
        self.opt_delim.grid(row=0, column=5, padx=5, pady=8, sticky="w")

        # 3. Large Text Box Preview
        f_text = ctk.CTkFrame(self, corner_radius=8)
        f_text.grid(row=2, column=0, sticky="nsew", padx=15, pady=(0, 10))
        f_text.grid_rowconfigure(0, weight=1)
        f_text.grid_columnconfigure(0, weight=1)

        self.txt_preview = ctk.CTkTextbox(
            f_text,
            font=ctk.CTkFont(family="Consolas", size=13),
            wrap="none",
        )
        self.txt_preview.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        # 4. Action Buttons Footer
        f_footer = ctk.CTkFrame(self, fg_color="transparent")
        f_footer.grid(row=3, column=0, sticky="ew", padx=15, pady=(0, 15))

        self.lbl_copied_msg = ctk.CTkLabel(
            f_footer,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#10b981",
        )
        self.lbl_copied_msg.pack(side="left", padx=5)

        btn_close = ctk.CTkButton(
            f_footer,
            text="Đóng",
            width=90,
            height=36,
            fg_color="#475569",
            hover_color="#334155",
            command=self.destroy,
        )
        btn_close.pack(side="right", padx=(5, 0))

        btn_save_txt = ctk.CTkButton(
            f_footer,
            text="💾 Lưu Tệp (.txt)",
            width=130,
            height=36,
            fg_color="#334155",
            hover_color="#1e293b",
            command=self._save_to_txt,
        )
        btn_save_txt.pack(side="right", padx=5)

        btn_copy = ctk.CTkButton(
            f_footer,
            text="📋 Sao Chép Vào Clipboard",
            width=210,
            height=36,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#7c3aed",
            hover_color="#6d28d9",
            command=self._copy_to_clipboard,
        )
        btn_copy.pack(side="right", padx=5)

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

    def _get_filtered_items(self) -> List[str]:
        filt = self.var_filter.get()
        fmt = self.var_format.get()

        valid_tasks = [t for t in self.tasks if t.current_code]
        if filt == "Chỉ BOM 1":
            valid_tasks = [t for t in valid_tasks if "1" in t.bom_type or "BOM 1" in t.bom_type]
        elif filt == "Chỉ BOM 2":
            valid_tasks = [t for t in valid_tasks if "2" in t.bom_type or "BOM 2" in t.bom_type]

        formatted_items = []
        for t in valid_tasks:
            code = t.current_code
            bom_tag = t.bom_type.replace(" ", "") if t.bom_type else "BOM"

            if "Mã (Loại BOM)" in fmt:
                formatted_items.append(f"{code} ({bom_tag})")
            elif "Chỉ Mã Số" in fmt:
                formatted_items.append(code)
            elif "Chi Tiết" in fmt:
                formatted_items.append(f"{t.original_name} -> {code} ({bom_tag})")

        return formatted_items

    def _update_text_preview(self):
        items = self._get_filtered_items()
        delim_choice = self.var_delim.get()

        if "Dấu phẩy" in delim_choice:
            separator = ", "
        elif "Xuống dòng" in delim_choice:
            separator = "\n"
        elif "Dấu chấm phẩy" in delim_choice:
            separator = "; "
        elif "Tab" in delim_choice:
            separator = "\t"
        else:
            separator = ", "

        full_text = separator.join(items)

        self.txt_preview.delete("1.0", "end")
        self.txt_preview.insert("1.0", full_text)
        self.lbl_copied_msg.configure(text=f"Đã tạo {len(items)} mục.")

    def _copy_to_clipboard(self):
        content = self.txt_preview.get("1.0", "end-1c")
        if not content.strip():
            messagebox.showwarning("Thông báo", "Không có nội dung để sao chép.")
            return

        self.clipboard_clear()
        self.clipboard_append(content)
        self.update()

        self.lbl_copied_msg.configure(
            text="✅ Đã sao chép thành công vào Clipboard!", text_color="#10b981"
        )

    def _save_to_txt(self):
        content = self.txt_preview.get("1.0", "end-1c")
        if not content.strip():
            messagebox.showwarning("Thông báo", "Không có nội dung để lưu.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text file", "*.txt"), ("All files", "*.*")],
            title="Lưu danh sách mã BOM",
            initialfile="danh_sach_BOM.txt",
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                messagebox.showinfo("Thành công", f"Đã lưu danh sách vào:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể lưu file: {e}")
