"""
Safe file renaming engine with conflict resolution and UTF-8 CSV logging.
"""

import os
import csv
from typing import List, Tuple, Dict, Callable, Optional
from datetime import datetime

from app.models import ImageTask, ProcessStatus, RenameRecord
from app.config import AppConfig


class RenameManager:
    """Handles conflict-free file renaming and CSV reporting."""

    @staticmethod
    def resolve_filename_conflicts(tasks: List[ImageTask], config: AppConfig) -> None:
        """
        Calculates unique new filenames for all tasks, handling:
        1. Collisions within the batch (e.g., two images with code 10025 -> 10025.jpg, 10025_1.jpg)
        2. Collisions with pre-existing files on disk.
        """
        # Track used filenames per folder: folder_path -> set(lower_cased_names)
        used_names_per_folder: Dict[str, set] = {}
        # Track counter per base name per folder: (folder_path, base_name) -> int
        name_counters: Dict[Tuple[str, str], int] = {}

        for task in tasks:
            if not task.is_successful or not task.current_code:
                task.new_filename = task.original_name
                task.new_file_path = task.file_path
                continue

            folder = os.path.dirname(task.file_path)
            if folder not in used_names_per_folder:
                # Populate existing files in folder (case-insensitive for Windows)
                try:
                    existing_files = {f.lower() for f in os.listdir(folder)}
                except Exception:
                    existing_files = set()
                used_names_per_folder[folder] = existing_files

            base_code = task.current_code
            if config.prefix:
                base_code = f"{config.prefix}{base_code}"
            if config.suffix:
                base_code = f"{base_code}{config.suffix}"

            ext = task.extension.lower()
            candidate_name = f"{base_code}{ext}"
            candidate_lower = candidate_name.lower()

            # If original file already matches desired name, keep it
            if task.original_name.lower() == candidate_lower:
                task.new_filename = task.original_name
                task.new_file_path = task.file_path
                continue

            # Resolve conflict if candidate_name is already taken
            if candidate_lower in used_names_per_folder[folder]:
                key = (folder, base_code.lower())
                counter = name_counters.get(key, 1)

                while True:
                    candidate_name = f"{base_code}_{counter}{ext}"
                    candidate_lower = candidate_name.lower()
                    if candidate_lower not in used_names_per_folder[folder]:
                        name_counters[key] = counter + 1
                        task.status = ProcessStatus.CONFLICT
                        break
                    counter += 1

            used_names_per_folder[folder].add(candidate_lower)
            task.new_filename = candidate_name
            task.new_file_path = os.path.join(folder, candidate_name)

    @classmethod
    def execute_renames(
        cls,
        tasks: List[ImageTask],
        config: AppConfig,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
    ) -> Tuple[int, int, List[RenameRecord]]:
        """
        Executes actual file renaming on the filesystem.
        Returns (success_count, failed_count, records_list).
        """
        cls.resolve_filename_conflicts(tasks, config)

        import gc
        import time
        gc.collect()  # Force release any temporary file handles

        success_count = 0
        failed_count = 0
        records: List[RenameRecord] = []
        total = len(tasks)

        for idx, task in enumerate(tasks):
            all_text_str = " | ".join(task.all_detected_text)
            extracted_code = task.current_code
            confidence = task.current_confidence

            if on_progress:
                on_progress(idx + 1, total, f"Đổi tên: {task.original_name} → {task.new_filename}")

            # If task has no valid code or was skipped
            if not task.is_successful or not task.new_filename:
                record = RenameRecord(
                    original_filename=task.original_name,
                    detected_text=all_text_str,
                    extracted_number=extracted_code,
                    bom_type=task.bom_type,
                    new_filename=task.original_name,
                    confidence=confidence,
                    status=task.status.value,
                    error_message=task.error_message or "Không tìm thấy mã hợp lệ",
                )
                records.append(record)
                failed_count += 1
                continue

            # If name is identical, skip actual renaming but record success
            if task.original_name == task.new_filename:
                task.status = ProcessStatus.RENAMED
                record = RenameRecord(
                    original_filename=task.original_name,
                    detected_text=all_text_str,
                    extracted_number=extracted_code,
                    bom_type=task.bom_type,
                    new_filename=task.new_filename,
                    confidence=confidence,
                    status="Đã đúng tên",
                )
                records.append(record)
                success_count += 1
                continue

            # Perform rename with retry
            src = task.file_path
            dst = task.new_file_path
            rename_success = False
            last_error = ""

            for attempt in range(3):
                try:
                    if os.path.exists(dst) and src.lower() != dst.lower():
                        raise FileExistsError(f"Tệp đích '{task.new_filename}' đã tồn tại.")

                    os.rename(src, dst)
                    task.file_path = dst
                    task.original_name = task.new_filename
                    task.status = ProcessStatus.RENAMED
                    success_count += 1
                    rename_success = True

                    record = RenameRecord(
                        original_filename=task.original_name,
                        detected_text=all_text_str,
                        extracted_number=extracted_code,
                        bom_type=task.bom_type,
                        new_filename=task.new_filename,
                        confidence=confidence,
                        status=ProcessStatus.RENAMED.value,
                    )
                    records.append(record)
                    break
                except Exception as e:
                    last_error = str(e)
                    gc.collect()
                    time.sleep(0.15)

            if not rename_success:
                task.status = ProcessStatus.FAILED
                task.error_message = last_error
                failed_count += 1

                record = RenameRecord(
                    original_filename=task.original_name,
                    detected_text=all_text_str,
                    extracted_number=extracted_code,
                    bom_type=task.bom_type,
                    new_filename=task.original_name,
                    confidence=confidence,
                    status=ProcessStatus.FAILED.value,
                    error_message=last_error,
                )
                records.append(record)

        return success_count, failed_count, records

    @staticmethod
    def export_csv(records: List[RenameRecord], output_path: str) -> bool:
        """
        Exports rename logs to CSV with UTF-8 BOM encoding for seamless Excel viewing.
        """
        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            fieldnames = [
                "original_filename",
                "bom_type",
                "extracted_number",
                "new_filename",
                "confidence",
                "status",
                "timestamp",
                "detected_text",
                "error_message",
            ]

            # Use utf-8-sig so Microsoft Excel displays Vietnamese characters properly
            with open(output_path, "w", newline="", encoding="utf-8-sig") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for rec in records:
                    writer.writerow(rec.to_dict())
            return True
        except Exception as e:
            print(f"[RenameManager] Error exporting CSV to {output_path}: {e}")
            return False
