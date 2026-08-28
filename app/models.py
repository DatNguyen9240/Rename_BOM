"""
Data models and Enums for AI OCR Batch Image Renamer.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Any, Dict
from datetime import datetime


class ProcessStatus(str, Enum):
    PENDING = "Chờ xử lý"
    PROCESSING = "Đang quét OCR..."
    SUCCESS = "Nhận diện thành công"
    NO_CANDIDATE = "Không tìm thấy mã hợp lệ"
    FAILED = "Lỗi xử lý"
    RENAMED = "Đã đổi tên"
    SKIPPED = "Bỏ qua"
    CONFLICT = "Trùng tên (Đã xử lý hậu tố)"


class ExtractionMode(str, Enum):
    REGEX = "Biểu thức chính quy (Regex)"
    DIGITS_ONLY = "Chỉ lấy số (Pure Digits)"
    ALPHANUMERIC = "Chữ và Số (Alphanumeric)"
    ALL_TEXT = "Toàn bộ Text"


@dataclass
class CandidateMatch:
    """Represents a potential extracted code or number from OCR results."""
    code: str
    confidence: float
    raw_text: str
    box_coords: Optional[List[List[float]]] = None
    is_corrected: bool = False
    correction_details: str = ""
    score: float = 0.0

    def get_display_text(self) -> str:
        corr_flag = " [Auto-fix]" if self.is_corrected else ""
        return f"{self.code} ({self.confidence:.1%}){corr_flag}"


@dataclass
class ImageTask:
    """Represents an image file item in the batch processing workflow."""
    task_id: str
    file_path: str
    original_name: str
    extension: str
    file_size_bytes: int = 0
    status: ProcessStatus = ProcessStatus.PENDING
    candidates: List[CandidateMatch] = field(default_factory=list)
    selected_candidate_index: int = 0
    custom_code_override: Optional[str] = None
    new_filename: str = ""
    all_detected_text: List[str] = field(default_factory=list)
    bom_type: str = ""  # "BOM 1", "BOM 2", hoặc ""
    error_message: str = ""

    @property
    def current_code(self) -> str:
        """Returns the currently active code (custom override or selected candidate)."""
        if self.custom_code_override is not None:
            return self.custom_code_override.strip()
        if self.candidates and 0 <= self.selected_candidate_index < len(self.candidates):
            return self.candidates[self.selected_candidate_index].code
        return ""

    @property
    def current_confidence(self) -> float:
        """Returns the confidence of the current candidate or 1.0 if custom override."""
        if self.custom_code_override is not None:
            return 1.0
        if self.candidates and 0 <= self.selected_candidate_index < len(self.candidates):
            return self.candidates[self.selected_candidate_index].confidence
        return 0.0

    @property
    def is_successful(self) -> bool:
        return bool(self.current_code) and self.status in [
            ProcessStatus.SUCCESS,
            ProcessStatus.CONFLICT,
            ProcessStatus.RENAMED,
        ]


@dataclass
class RenameRecord:
    """Log record formatted for CSV export and audit tracking."""
    original_filename: str
    detected_text: str
    extracted_number: str
    bom_type: str = ""
    new_filename: str = ""
    confidence: float = 0.0
    status: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_filename": self.original_filename,
            "bom_type": self.bom_type,
            "extracted_number": self.extracted_number,
            "new_filename": self.new_filename,
            "confidence": f"{self.confidence:.2%}" if self.confidence > 0 else "N/A",
            "status": self.status,
            "timestamp": self.timestamp,
            "detected_text": self.detected_text,
            "error_message": self.error_message
        }
