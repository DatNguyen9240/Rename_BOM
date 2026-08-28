import pypdfium2 as pdfium
import numpy as np
import cv2
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from app.ocr_engine import OCREngine
from app.filename_extractor import FilenameExtractor
from app.config import AppConfig

pdf_path = r'D:\quet\8058991CTIM21-04.pdf'
pdf = pdfium.PdfDocument(pdf_path)
page = pdf.get_page(0)
bmp = page.render(scale=1.3)
pil_img = bmp.to_pil()
rgb_arr = np.array(pil_img)
bgr_arr = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)

engine = OCREngine.get_instance(lang='ch', use_angle_cls=True)
results = engine.recognize(bgr_arr)

print(f'Total OCR lines detected: {len(results)}')
for idx, (box, text, score) in enumerate(results):
    print(f'[{idx+1:02d}] (score: {score:.3f}) -> "{text}"')

config = AppConfig()
config.regex_pattern = r'[0-9A-Za-z]{6,15}-[0-9]{2}'
extractor = FilenameExtractor(config)
candidates = extractor.extract_candidates(results)
print('\n=== Candidates Found ===')
for c in candidates:
    print(f'Code: {c.code}, Conf: {c.confidence:.3f}, Raw: {c.raw_text}')
