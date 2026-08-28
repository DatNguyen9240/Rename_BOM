"""
Configuration management for AI OCR Batch Image Renamer.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, Any


CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


@dataclass
class AppConfig:
    # --- OCR Settings ---
    ocr_language: str = "en"  # Options: en, ch, vi, latin
    use_angle_cls: bool = True
    use_gpu: bool = False
    confidence_threshold: float = 0.50  # 50%

    # --- Extraction & Pattern Rules ---
    extraction_mode: str = "Biểu thức chính quy (Regex)"
    regex_pattern: str = r"[0-9A-Za-z]{6,15}-[0-9]{2}"  # Pattern chuẩn cho Số BV CHENKAI (VD: 8058991CTIM21-04)
    min_length: int = 8
    max_length: int = 25
    match_entire_token_only: bool = False

    # --- Heuristic Character Disambiguation / Correction ---
    enable_disambiguation: bool = True
    correct_o_to_zero: bool = True       # 'O' / 'o' -> '0' when expecting digits
    correct_i_to_one: bool = True        # 'I' / 'l' / '|' -> '1' when expecting digits
    correct_s_to_five: bool = True       # 'S' / 's' -> '5' when expecting digits
    correct_b_to_eight: bool = True      # 'B' -> '8' (VD: B0S -> 805)
    correct_z_to_two: bool = False       # 'Z' -> '2'

    # --- Image Preprocessing Settings ---
    enable_preprocessing: bool = True
    auto_rotate_exif: bool = True
    to_grayscale: bool = True
    max_dimension: int = 2000            # Resize large image to max width/height to boost speed
    enhance_contrast_clahe: bool = True
    clahe_clip_limit: float = 2.5
    sharpen_image: bool = True
    adaptive_threshold: bool = False

    # --- Renaming & File Settings ---
    prefix: str = ""
    suffix: str = ""
    case_format: str = "AS_IS"           # UPPER, LOWER, AS_IS
    keep_original_extension: bool = True
    append_counter_for_duplicates: bool = True
    supported_extensions: list = field(default_factory=lambda: [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".pdf"])

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    def save(self, filepath: str = CONFIG_FILE_PATH) -> bool:
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[Config] Error saving config: {e}")
            return False

    @classmethod
    def load(cls, filepath: str = CONFIG_FILE_PATH) -> "AppConfig":
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return cls.from_dict(data)
            except Exception as e:
                print(f"[Config] Error loading config: {e}. Using defaults.")
        return cls()
