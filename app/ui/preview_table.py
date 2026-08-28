"""
CustomTkinter integrated Treeview table for previewing, candidate selection, and manual editing.
"""

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import customtkinter as ctk
from typing import List, Optional, Callable

from app.models import ImageTask, ProcessStatus
from app.ui.image_preview_modal import ImagePreviewModal


class PreviewTable(ctk.CTkFrame):
    """Interactive preview table component displaying files, OCR results, and rename targets."""

    def __init__(
        self,
        parent,
        on_task_modified: Optional[Callable[[ImageTask], None]] = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        self.on_task_modified = on_task_modified
        self.tasks: List[ImageTask] = []
        self._task_map = {}  # tree_item_id -> ImageTask

        self._init_style()
        self._build_ui()
        self._setup_events()

    def _init_style(self):
        """Applies modern styling to ttk.Treeview matching dark mode theme."""
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Configure colors
        bg_color = "#1e293b"
        fg_color = "#f8fafc"
        select_bg = "#3b82f6"
        header_bg = "#0f172a"
        header_fg = "#94a3b8"

        self.style.configure(
            "Custom.Treeview",
            background=bg_color,
            foreground=fg_color,
            fieldbackground=bg_color,
            rowheight=32,
            font=("Segoe UI", 10),
            borderwidth=0,
        )
        self.style.configure(
            "Custom.Treeview.Heading",
            background=header_bg,
            foreground=header_fg,
            font=("Segoe UI", 10, "bold"),
            borderwidth=1,
            relief="flat",
            padding=6,
        )
        self.style.map(
            "Custom.Treeview",
            background=[("selected", select_bg)],
            foreground=[("selected", "#ffffff")],
        )
        self.style.map(
            "Custom.Treeview.Heading",
            background=[("active", "#1e293b")],
            foreground=[("active", "#ffffff")],
        )

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        columns = ("idx", "orig_name", "code", "bom_type", "new_name", "conf", "status", "cand_count")

        self.tree = ttk.Treeview(
            self,
            columns=columns,
            show="headings",
            style="Custom.Treeview",
            selectmode="extended",
        )

        # Configure columns
        self.tree.heading("idx", text="#", anchor="center")
        self.tree.heading("orig_name", text="Tên File Gốc", anchor="w")
        self.tree.heading("code", text="Mã Nhận Diện", anchor="w")
        self.tree.heading("bom_type", text="Loại BOM", anchor="center")
        self.tree.heading("new_name", text="Tên Mới Dự Kiến", anchor="w")
        self.tree.heading("conf", text="Độ Tin Cậy", anchor="center")
        self.tree.heading("status", text="Trạng Thái", anchor="w")
        self.tree.heading("cand_count", text="Số Ứng Viên", anchor="center")

        self.tree.column("idx", width=45, minwidth=35, anchor="center", stretch=False)
        self.tree.column("orig_name", width=200, minwidth=140, anchor="w")
        self.tree.column("code", width=170, minwidth=120, anchor="w")
        self.tree.column("bom_type", width=95, minwidth=75, anchor="center", stretch=False)
        self.tree.column("new_name", width=200, minwidth=140, anchor="w")
        self.tree.column("conf", width=90, minwidth=75, anchor="center", stretch=False)
        self.tree.column("status", width=170, minwidth=120, anchor="w")
        self.tree.column("cand_count", width=90, minwidth=70, anchor="center", stretch=False)

        # Scrollbars
        self.vsb = ctk.CTkScrollbar(self, orientation="vertical", command=self.tree.yview)
        self.hsb = ctk.CTkScrollbar(self, orientation="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")
        self.hsb.grid(row=1, column=0, sticky="ew")

        # Color Tags
        self.tree.tag_configure("success", foreground="#34d399")
        self.tree.tag_configure("conflict", foreground="#fbbf24")
        self.tree.tag_configure("failed", foreground="#f87171")
        self.tree.tag_configure("no_candidate", foreground="#94a3b8")
        self.tree.tag_configure("renamed", foreground="#60a5fa")
        self.tree.tag_configure("processing", foreground="#38bdf8")

    def _setup_events(self):
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Button-3>", self._on_right_click)

    def set_tasks(self, tasks: List[ImageTask]):
        """Populates the table with image tasks."""
        self.tasks = tasks
        self.refresh()

    def refresh(self):
        """Redraws all rows in the table."""
        self.tree.delete(*self.tree.get_children())
        self._task_map.clear()

        for idx, task in enumerate(self.tasks, start=1):
            conf_str = f"{task.current_confidence:.1%}" if task.current_confidence > 0 else "-"
            cand_count_str = str(len(task.candidates)) if task.candidates else "0"
            bom_str = task.bom_type if task.bom_type else "-"

            # Tag determination
            tag = "default"
            if task.status == ProcessStatus.SUCCESS:
                tag = "success"
            elif task.status == ProcessStatus.CONFLICT:
                tag = "conflict"
            elif task.status == ProcessStatus.FAILED:
                tag = "failed"
            elif task.status == ProcessStatus.NO_CANDIDATE:
                tag = "no_candidate"
            elif task.status == ProcessStatus.RENAMED:
                tag = "renamed"
            elif task.status == ProcessStatus.PROCESSING:
                tag = "processing"

            item_id = self.tree.insert(
                "",
                "end",
                values=(
                    idx,
                    task.original_name,
                    task.current_code or "---",
                    bom_str,
                    task.new_filename or task.original_name,
                    conf_str,
                    task.status.value,
                    cand_count_str,
                ),
                tags=(tag,),
            )
            self._task_map[item_id] = task

    def update_task_row(self, task: ImageTask):
        """Updates a specific task's row in the table."""
        for item_id, t in self._task_map.items():
            if t.task_id == task.task_id:
                conf_str = f"{task.current_confidence:.1%}" if task.current_confidence > 0 else "-"
                cand_count_str = str(len(task.candidates)) if task.candidates else "0"
                bom_str = task.bom_type if task.bom_type else "-"

                tag = "default"
                if task.status == ProcessStatus.SUCCESS:
                    tag = "success"
                elif task.status == ProcessStatus.CONFLICT:
                    tag = "conflict"
                elif task.status == ProcessStatus.FAILED:
                    tag = "failed"
                elif task.status == ProcessStatus.NO_CANDIDATE:
                    tag = "no_candidate"
                elif task.status == ProcessStatus.RENAMED:
                    tag = "renamed"
                elif task.status == ProcessStatus.PROCESSING:
                    tag = "processing"

                self.tree.item(
                    item_id,
                    values=(
                        self.tasks.index(task) + 1,
                        task.original_name,
                        task.current_code or "---",
                        bom_str,
                        task.new_filename or task.original_name,
                        conf_str,
                        task.status.value,
                        cand_count_str,
                    ),
                    tags=(tag,),
                )
                break

    def get_selected_task(self) -> Optional[ImageTask]:
        selected = self.tree.selection()
        if selected and selected[0] in self._task_map:
            return self._task_map[selected[0]]
        return None

    def _on_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id or item_id not in self._task_map:
            return
        task = self._task_map[item_id]
        ImagePreviewModal(self, task)

    def _on_right_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        self.tree.selection_set(item_id)
        task = self._task_map.get(item_id)
        if not task:
            return

        menu = tk.Menu(self, tearoff=0, bg="#1e293b", fg="#f8fafc", activebackground="#3b82f6")

        menu.add_command(
            label="👁️ Xem ảnh & Bounding Box...",
            command=lambda: ImagePreviewModal(self, task),
        )
        menu.add_command(
            label="✏️ Nhập sửa mã thủ công...",
            command=lambda: self._prompt_manual_edit(task),
        )

        # Candidates Submenu
        if task.candidates:
            cand_menu = tk.Menu(menu, tearoff=0, bg="#1e293b", fg="#f8fafc", activebackground="#3b82f6")
            for idx, cand in enumerate(task.candidates):
                prefix = "✓ " if (idx == task.selected_candidate_index and task.custom_code_override is None) else "   "
                cand_menu.add_command(
                    label=f"{prefix}{cand.get_display_text()}",
                    command=lambda i=idx, t=task: self._select_candidate(t, i),
                )
            menu.add_cascade(label="🔀 Chọn ứng viên khác (Candidates)...", menu=cand_menu)

        menu.add_separator()
        menu.add_command(
            label="🚫 Giữ nguyên tên gốc (Bỏ qua)",
            command=lambda: self._skip_task(task),
        )

        menu.tk_popup(event.x_root, event.y_root)

    def _prompt_manual_edit(self, task: ImageTask):
        current_val = task.current_code or ""
        new_val = simpledialog.askstring(
            "Sửa Mã Thủ Công",
            f"Nhập mã mới cho file '{task.original_name}':",
            initialvalue=current_val,
            parent=self,
        )
        if new_val is not None:
            new_val = new_val.strip()
            if new_val:
                task.custom_code_override = new_val
                task.status = ProcessStatus.SUCCESS
            else:
                task.custom_code_override = None
                task.status = ProcessStatus.NO_CANDIDATE if not task.candidates else ProcessStatus.SUCCESS

            if self.on_task_modified:
                self.on_task_modified(task)
            self.update_task_row(task)

    def _select_candidate(self, task: ImageTask, candidate_idx: int):
        task.selected_candidate_index = candidate_idx
        task.custom_code_override = None
        task.status = ProcessStatus.SUCCESS
        if self.on_task_modified:
            self.on_task_modified(task)
        self.update_task_row(task)

    def _skip_task(self, task: ImageTask):
        task.custom_code_override = ""
        task.status = ProcessStatus.SKIPPED
        task.new_filename = task.original_name
        if self.on_task_modified:
            self.on_task_modified(task)
        self.update_task_row(task)
