"""
Thread-safe wrapper around PaddleOCR engine with caching and error isolation.
"""

import os
import threading
from typing import List, Tuple, Optional, Any
import numpy as np


class OCREngine:
    """Manages local PaddleOCR inference with lazy loading and thread safety."""

    _instance: Optional["OCREngine"] = None
    _lock = threading.Lock()

    def __init__(self, lang: str = "ch", use_angle_cls: bool = True, use_gpu: bool = False):
        self.lang = lang
        self.use_angle_cls = use_angle_cls
        self.use_gpu = use_gpu
        self._engine: Any = None
        self._engine_lang: str = ""
        self._initialized = False

    @classmethod
    def get_instance(
        cls, lang: str = "ch", use_angle_cls: bool = True, use_gpu: bool = False
    ) -> "OCREngine":
        """Singleton accessor to prevent reloading heavy models."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(lang=lang, use_angle_cls=use_angle_cls, use_gpu=use_gpu)
            else:
                # Update config if language or parameters changed
                if cls._instance.lang != lang or cls._instance.use_gpu != use_gpu:
                    cls._instance.lang = lang
                    cls._instance.use_gpu = use_gpu
                    cls._instance._engine = None  # Reload with new language
                    cls._instance._initialized = False
            return cls._instance

    def _init_engine(self) -> None:
        """Initializes PaddleOCR model instance."""
        if self._engine is not None and self._engine_lang == self.lang:
            return

        try:
            # Patch PaddleStaticRunner for Windows CPU stability
            try:
                import paddle.inference as paddle_inference
                from paddlex.inference.models.runners.paddle_static.runner import (
                    PaddleStaticRunner,
                    get_model_paths,
                )

                def patched_create(runner_self):
                    model_paths = get_model_paths(runner_self.model_dir, runner_self.model_file_prefix)
                    model_file, params_file = model_paths["paddle"]
                    config = paddle_inference.Config(str(model_file), str(params_file))
                    if runner_self._config.get("device_type") == "gpu" and self.use_gpu:
                        config.enable_use_gpu(100, 0)
                    else:
                        config.disable_gpu()
                        config.disable_mkldnn()
                    config.set_cpu_math_library_num_threads(4)
                    config.disable_glog_info()
                    return paddle_inference.create_predictor(config)

                PaddleStaticRunner._create = patched_create
            except Exception as patch_err:
                print(f"[OCREngine] Static runner patch note: {patch_err}")

            from paddleocr import PaddleOCR

            # Initialize PaddleOCR
            try:
                self._engine = PaddleOCR(
                    ocr_version="PP-OCRv4",
                    lang=self.lang,
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=self.use_angle_cls,
                )
            except TypeError:
                # Fallback for older PaddleOCR versions
                self._engine = PaddleOCR(
                    use_angle_cls=self.use_angle_cls,
                    lang=self.lang,
                    use_gpu=self.use_gpu,
                    show_log=False,
                )

            self._engine_lang = self.lang
            self._initialized = True
        except ImportError:
            raise RuntimeError(
                "Thư viện PaddleOCR chưa được cài đặt. "
                "Vui lòng chạy: pip install paddlepaddle paddleocr"
            )
        except Exception as e:
            raise RuntimeError(f"Lỗi khởi tạo PaddleOCR engine ({self.lang}): {e}")

    def recognize(
        self, image_input: np.ndarray
    ) -> List[Tuple[List[List[float]], str, float]]:
        """
        Runs OCR on a numpy BGR/RGB image.
        Returns a list of tuples: (bounding_box_points, text, confidence).
        """
        if image_input is None or image_input.size == 0:
            return []

        with self._lock:
            self._init_engine()

            parsed_boxes: List[Tuple[List[List[float]], str, float]] = []

            try:
                # PaddleOCR 3.x with Paddlex uses predict()
                if hasattr(self._engine, "predict"):
                    # Convert BGR to RGB for predict if needed
                    if len(image_input.shape) == 3 and image_input.shape[2] == 3:
                        import cv2
                        rgb = cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB)
                    else:
                        rgb = image_input

                    results = list(self._engine.predict(rgb))
                    if results and isinstance(results[0], dict):
                        r = results[0]
                        rec_texts = r.get("rec_texts", r.get("rec_text", []))
                        rec_scores = r.get("rec_scores", r.get("rec_score", []))
                        dt_polys = r.get("dt_polys", r.get("rec_polys", []))

                        for poly, text, score in zip(dt_polys, rec_texts, rec_scores):
                            text_clean = str(text).strip()
                            if text_clean:
                                box = poly.tolist() if isinstance(poly, np.ndarray) else poly
                                parsed_boxes.append((box, text_clean, float(score)))
                        return parsed_boxes
                else:
                    results = self._engine.ocr(image_input, cls=self.use_angle_cls)
            except Exception as e:
                # Fallback to standard ocr() method
                try:
                    results = self._engine.ocr(image_input)
                except Exception as e2:
                    print(f"[OCREngine] OCR inference error: {e2}")
                    return []

        if not results or results[0] is None:
            return parsed_boxes

        # Handle legacy paddleocr output format
        for line in results[0]:
            if not line or len(line) < 2:
                continue
            box = line[0]  # [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
            text_score = line[1]  # (text, confidence)
            if isinstance(text_score, (tuple, list)) and len(text_score) >= 2:
                text = str(text_score[0]).strip()
                conf = float(text_score[1])
                if text:
                    parsed_boxes.append((box, text, conf))

        return parsed_boxes
