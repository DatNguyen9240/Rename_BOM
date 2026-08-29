"""
Automated unit tests for AI OCR Batch Image Renamer modules.
"""

import os
import sys
import unittest
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import AppConfig
from app.models import ImageTask, ProcessStatus, CandidateMatch, RenameRecord
from app.filename_extractor import FilenameExtractor
from app.image_processor import ImageProcessor
from app.rename_manager import RenameManager


class TestOCRComponents(unittest.TestCase):

    def setUp(self):
        self.config = AppConfig()

    def test_image_processor_pipeline(self):
        # Create a synthetic 100x100 RGB image
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[30:70, 30:70] = 255  # white square in the center

        processed = ImageProcessor.preprocess_for_ocr(img, self.config)
        self.assertIsNotNone(processed)
        self.assertEqual(len(processed.shape), 3)

        # Test resizing
        resized, scale = ImageProcessor.resize_keep_aspect_ratio(img, max_dim=50)
        self.assertEqual(max(resized.shape[:2]), 50)
        self.assertAlmostEqual(scale, 0.5)

    def test_filename_extractor_regex(self):
        self.config.regex_pattern = r"904Y\d{8}"
        self.config.min_length = 8
        self.config.max_length = 15
        extractor = FilenameExtractor(self.config)

        # Simulated OCR results: [(box, text, confidence)]
        ocr_results = [
            ([[0, 0], [10, 0], [10, 10], [0, 10]], "CONG TY TNHH ABC", 0.95),
            ([[0, 20], [100, 20], [100, 40], [0, 40]], "Mã sản phẩm: 904Y10200001", 0.98),
            ([[0, 50], [50, 50], [50, 60], [0, 60]], "Ngay: 2026-08-28", 0.88),
        ]

        candidates = extractor.extract_candidates(ocr_results)
        self.assertTrue(len(candidates) >= 1)
        best = candidates[0]
        self.assertEqual(best.code, "904Y10200001")
        self.assertAlmostEqual(best.confidence, 0.98)

    def test_disambiguation_correction(self):
        self.config.regex_pattern = r"\b\d{5}\b"
        self.config.min_length = 5
        self.config.max_length = 5
        self.config.enable_disambiguation = True
        self.config.correct_o_to_zero = True
        self.config.correct_i_to_one = True
        self.config.correct_s_to_five = True

        extractor = FilenameExtractor(self.config)

        # '1OO25' contains letter O instead of zero 0
        ocr_results = [
            ([[0, 0], [50, 0], [50, 20], [0, 20]], "Mã: 1OO25", 0.92),
        ]

        candidates = extractor.extract_candidates(ocr_results)
        self.assertTrue(any(c.code == "10025" for c in candidates))
        corr_cand = next(c for c in candidates if c.code == "10025")
        self.assertTrue(corr_cand.is_corrected)

    def test_rename_manager_conflict_resolution(self):
        tasks = [
            ImageTask(
                task_id="1",
                file_path="/images/IMG_001.jpg",
                original_name="IMG_001.jpg",
                extension=".jpg",
                status=ProcessStatus.SUCCESS,
                candidates=[CandidateMatch(code="10025", confidence=0.95, raw_text="10025")],
            ),
            ImageTask(
                task_id="2",
                file_path="/images/IMG_002.jpg",
                original_name="IMG_002.jpg",
                extension=".jpg",
                status=ProcessStatus.SUCCESS,
                candidates=[CandidateMatch(code="10025", confidence=0.92, raw_text="10025")],
            ),
            ImageTask(
                task_id="3",
                file_path="/images/IMG_003.jpg",
                original_name="IMG_003.jpg",
                extension=".jpg",
                status=ProcessStatus.NO_CANDIDATE,
                candidates=[],
            ),
        ]

        RenameManager.resolve_filename_conflicts(tasks, self.config)

        self.assertEqual(tasks[0].new_filename, "10025.jpg")
        self.assertEqual(tasks[1].new_filename, "10025_1.jpg")
        self.assertEqual(tasks[1].status, ProcessStatus.CONFLICT)
        self.assertEqual(tasks[2].new_filename, "IMG_003.jpg")  # kept original

    def test_export_csv_report(self):
        records = [
            RenameRecord(
                original_filename="IMG_001.jpg",
                detected_text="904Y10200001",
                extracted_number="904Y10200001",
                bom_type="BOM 1",
                new_filename="904Y10200001.jpg",
                confidence=0.98,
                status="Đã đổi tên",
            )
        ]
        test_csv = os.path.join(os.path.dirname(__file__), "test_log.csv")
        success = RenameManager.export_csv(records, test_csv)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(test_csv))
        if os.path.exists(test_csv):
            os.remove(test_csv)

    def test_bom_classification(self):
        extractor = FilenameExtractor(self.config)
        
        # Test BOM 2
        ocr_bom2 = [
            ([[0, 0], [10, 0], [10, 10], [0, 10]], "CHEN KAI PRECISION INDUSTRY CO., LTD", 0.99),
            ([[0, 10], [10, 10], [10, 20], [0, 20]], "THONG TIN CO BAN VE SAN PHAM(BOM2)", 0.98),
            ([[0, 20], [10, 20], [10, 30], [0, 30]], "产品(BOM2)基础资料", 0.98),
        ]
        self.assertEqual(extractor.detect_bom_type(ocr_bom2), "BOM 2")

        # Test BOM 1
        ocr_bom1 = [
            ([[0, 0], [10, 0], [10, 10], [0, 10]], "CHEN KAI PRECISION INDUSTRY CO., LTD", 0.99),
            ([[0, 10], [10, 10], [10, 20], [0, 20]], "THONG TIN CO BAN VE SAN PHAM(BOM)", 0.98),
            ([[0, 20], [10, 20], [10, 30], [0, 30]], "产品(BOM)基础资料", 0.98),
        ]
        self.assertEqual(extractor.detect_bom_type(ocr_bom1), "BOM 1")

        # Test BOM 2 with OCR zero/O and spacing
        ocr_bom2_variant = [
            ([[0, 0], [10, 0], [10, 10], [0, 10]], "THONG TIN SAN PHAM (B0M 2)", 0.95),
        ]
        self.assertEqual(extractor.detect_bom_type(ocr_bom2_variant), "BOM 2")

    def test_false_positive_rejection(self):
        self.config.regex_pattern = r"[0-9A-Za-z]{6,15}-[0-9]{2}"
        self.config.min_length = 8
        self.config.max_length = 25
        extractor = FilenameExtractor(self.config)

        # False positives like 'Số mục: P03-02' -> 'SomuP03-02'
        ocr_false_positives = [
            ([[0, 0], [10, 0], [10, 10], [0, 10]], "Số mục: P03-02", 0.95),
            ([[0, 10], [10, 10], [10, 20], [0, 20]], "SomuP03-02", 0.92),
            ([[0, 20], [10, 20], [10, 30], [0, 30]], "Số trang: 01-02", 0.90),
            ([[0, 30], [10, 30], [10, 40], [0, 40]], "Số lượng: 100-00", 0.88),
        ]
        candidates = extractor.extract_candidates(ocr_false_positives)
        self.assertEqual(len(candidates), 0, "Non-code metadata like SomuP03-02 must be rejected.")

    def test_drawing_code_priority_over_metadata(self):
        self.config.regex_pattern = r"[0-9A-Za-z]{6,15}-[0-9]{2}"
        self.config.min_length = 8
        self.config.max_length = 25
        extractor = FilenameExtractor(self.config)

        # Real drawing code mixed with metadata headers
        ocr_mixed = [
            ([[0, 0], [10, 0], [10, 10], [0, 10]], "Số mục: P03-02", 0.98),
            ([[0, 10], [10, 10], [10, 20], [0, 20]], "Số BV: 8052521XTIE00-01", 0.95),
        ]
        candidates = extractor.extract_candidates(ocr_mixed)
        self.assertTrue(len(candidates) >= 1)
        self.assertEqual(candidates[0].code, "8052521XTIE00-01")


if __name__ == "__main__":
    unittest.main()

