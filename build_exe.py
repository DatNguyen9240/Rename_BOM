"""
Automated PyInstaller build script for packaging AI OCR Batch Image Renamer into a Windows executable.
"""

import os
import sys
import subprocess
import shutil


def get_customtkinter_path():
    try:
        import customtkinter
        return os.path.dirname(customtkinter.__file__)
    except ImportError:
        print("[Build] Warning: customtkinter is not installed in current environment.")
        return None


def get_paddleocr_path():
    try:
        import paddleocr
        return os.path.dirname(paddleocr.__file__)
    except ImportError:
        print("[Build] Warning: paddleocr is not installed in current environment.")
        return None


def build_executable():
    print("==================================================")
    print("🚀 ĐANG ĐÓNG GÓI ỨNG DỤNG AI OCR RENAMER BẰNG PYINSTALLER")
    print("==================================================")

    root_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(root_dir, "app", "main.py")
    dist_dir = os.path.join(root_dir, "dist")
    build_dir = os.path.join(root_dir, "build")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=AI_OCR_Image_Renamer",
        "--onedir",             # onedir recommended for heavy OCR libraries to speed up launch
        "--windowed",           # hide console window
        "--clean",
        "--noconfirm",
    ]

    # Add customtkinter data
    ctk_path = get_customtkinter_path()
    if ctk_path and os.path.exists(ctk_path):
        cmd.extend(["--add-data", f"{ctk_path};customtkinter/"])

    # Add paddleocr data
    ocr_path = get_paddleocr_path()
    if ocr_path and os.path.exists(ocr_path):
        cmd.extend(["--add-data", f"{ocr_path};paddleocr/"])

    # Hidden imports for PaddleOCR and standard dependencies
    hidden_imports = [
        "customtkinter",
        "paddleocr",
        "paddle",
        "paddlex",
        "pypdfium2",
        "pypdfium2_raw",
        "cv2",
        "PIL",
        "PIL.Image",
        "PIL.ImageOps",
        "PIL.ImageTk",
        "numpy",
        "pandas",
        "pyclipper",
        "shapely",
        "skimage",
        "scipy",
    ]
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    # Target entry point
    cmd.append(main_script)

    print(f"\n[Command] {' '.join(cmd)}\n")
    try:
        subprocess.run(cmd, check=True)
        print("\n==================================================")
        print("🎉 ĐÓNG GÓI HOÀN TẤT!")
        print(f"📁 Thư mục file thực thi: {os.path.join(dist_dir, 'AI_OCR_Image_Renamer')}")
        print(f"🚀 File chạy: {os.path.join(dist_dir, 'AI_OCR_Image_Renamer', 'AI_OCR_Image_Renamer.exe')}")
        print("==================================================")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Lỗi trong quá trình build: {e}")


if __name__ == "__main__":
    build_executable()
