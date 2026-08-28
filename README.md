# 🏷️ AI OCR Batch Image Renamer (Local Offline)

Ứng dụng Python AI OCR chạy hoàn toàn **Local 100% (Offline, bảo mật tuyệt đối)** sử dụng **PaddleOCR** và giao diện **CustomTkinter** hiện đại. Tool tự động quét hàng loạt hình ảnh, nhận diện số/mã sản phẩm theo cấu hình Regex, hiển thị bảng xem trước (Preview) thông minh, và đổi tên file an toàn chống trùng lặp.

---

## 🌟 Tính Năng Nổi Bật

1. **OCR Offline 100% với PaddleOCR**: Nhận diện siêu nhanh và chính xác không cần kết nối mạng hay cloud.
2. **Bộ Tiền Xử Lý Ảnh Chuyên Sâu**:
   - Tự động xoay ảnh theo EXIF Orientation.
   - Cân bằng tương phản cục bộ **CLAHE** (làm rõ chữ mờ, chữ dập kim loại).
   - Làm sắc nét nét chữ (**Unsharp Mask / Sharpening**).
   - Nhị phân hóa thích nghi (**Adaptive Threshold**).
3. **Bóc Tách & Lọc Mã Thông Minh**:
   - Tùy biến Regex linh hoạt (`\b\d{4,10}\b`, `904Y\d{8}`, `[A-Z0-9-]{6,16}`).
   - Cơ chế sửa nhầm lẫn ký tự OCR theo ngữ cảnh (`O → 0`, `I → 1`, `S → 5`, `B → 8`, `Z → 2`).
   - Xếp hạng & hiển thị toàn bộ danh sách ứng viên (**Candidates**) kèm điểm tin cậy (**Confidence %**).
4. **Xem Trước (Preview) & Tương Tác Trực Quan**:
   - Bảng hiển thị: Tên gốc, Mã tìm thấy, Tên mới dự kiến, Độ tin cậy, Trạng thái.
   - **Nhấp đúp chuột**: Phóng to ảnh và hiển thị khung viền (**Bounding Box**) vị trí chữ nhận diện được trên ảnh.
   - **Chuột phải**: Cho phép chọn ứng viên khác hoặc sửa tay trực tiếp.
5. **Đổi Tên File An Toàn Tuyệt Đối**:
   - Chỉ đổi tên khi người dùng bấm nút **"Đổi Tên (Rename)"**.
   - Tự động xử lý trùng tên: `10025.jpg` → `10025_1.jpg`, `10025_2.jpg`.
   - File lỗi hoặc không tìm thấy mã sẽ giữ nguyên tên gốc, gắn cờ `FAILED`.
   - Hỗ trợ đường dẫn có dấu Tiếng Việt (**Unicode Paths**) trên Windows không bị lỗi.
6. **Xuất Báo Cáo CSV Chuẩn**:
   - Lưu đầy đủ log: `original_filename`, `detected_text`, `extracted_number`, `new_filename`, `confidence`, `status`, `timestamp`.
   - Mã hóa `UTF-8 with BOM` giúp mở trực tiếp trên Excel không bao giờ bị lỗi font.

---

## 📂 Cấu Trúc Thư Mục Dự Án

```
d:/Dat/
├── app/
│   ├── __init__.py
│   ├── config.py                 # Quản lý tham số cấu hình & lưu file config.json
│   ├── models.py                 # Data models: ImageTask, CandidateMatch, RenameRecord
│   ├── image_processor.py        # Tiền xử lý ảnh (Unicode loading, CLAHE, Sharpen, Grayscale)
│   ├── ocr_engine.py             # Wrapper PaddleOCR Singleton đa luồng
│   ├── filename_extractor.py     # Bộ lọc regex, xếp hạng candidate & sửa nhầm ký tự
│   ├── rename_manager.py         # Đổi tên file an toàn, chống trùng lặp, xuất CSV
│   ├── main.py                   # Điểm khởi chạy ứng dụng (Entry point)
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py        # Giao diện chính CustomTkinter
│       ├── preview_table.py      # Bảng Treeview Dark Mode xem trước & sửa tay
│       ├── settings_dialog.py    # Hộp thoại cài đặt tham số nâng cao
│       └── image_preview_modal.py # Xem phóng to ảnh & vẽ Bounding Box
├── tests/
│   └── test_components.py        # Bộ kiểm thử tự động (Unit tests)
├── build_exe.py                  # Script tự động đóng gói file .exe
├── requirements.txt              # Danh sách thư viện Python
└── README.md                     # Hướng dẫn chi tiết
```

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy Chương Trình

### Bước 1: Cài đặt Python
- Tải và cài đặt **Python 3.10** hoặc **Python 3.11** (khuyên dùng 64-bit) từ trang chủ: [python.org](https://www.python.org/downloads/).
- ⚠️ **Lưu ý quan trọng**: Khi cài đặt, hãy tích chọn **"Add Python to PATH"**.

### Bước 2: Mở Terminal (PowerShell / CMD) và chuyển vào thư mục dự án
```powershell
cd d:\Dat
```

### Bước 3: Tạo & Kích hoạt Virtual Environment (Khuyên Dùng)
```powershell
# Tạo môi trường ảo venv
python -m venv venv

# Kích hoạt venv trên Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Hoặc nếu dùng CMD thông thường:
venv\Scripts\activate.bat
```

### Bước 4: Cài đặt các thư viện phụ thuộc (Dependencies)
```powershell
# Cài đặt PaddlePaddle (bản CPU chuẩn cho máy tính thông thường)
pip install paddlepaddle -i https://mirror.baidu.com/pypi/simple

# Cài đặt các thư viện còn lại
pip install -r requirements.txt
```

> 💡 *Nếu máy tính có card đồ họa NVIDIA CUDA và muốn tăng tốc tối đa, bạn có thể cài `paddlepaddle-gpu` theo hướng dẫn tại [paddlepaddle.org.cn](https://www.paddlepaddle.org.cn/).*

### Bước 5: Chạy ứng dụng
```powershell
python app/main.py
```

---

## 📖 Hướng Dẫn Sử Dụng Chi Tiết

1. **Bước 1 - Chọn thư mục**: Bấm nút **"📁 Chọn Thư Mục Ảnh"** và chọn thư mục chứa các file `.jpg`, `.png`, `.webp` cần đổi tên.
2. **Bước 2 - Chọn quy tắc lọc mã**:
   - Chọn mẫu có sẵn trong menu **"Mẫu nhận diện"** (VD: *Chữ và Số*, *Chỉ lấy số*, *Mã sản phẩm*).
   - Hoặc gõ Regex theo định dạng mong muốn (VD: mã dạng `904Y10200001` thì nhập `904Y\d{8}`).
   - Chỉnh độ dài tối thiểu / tối đa của chuỗi mã.
3. **Bước 3 - Quét OCR**: Bấm **"🚀 Bắt Đầu Quét OCR"**. Ứng dụng sẽ xử lý ngầm và hiển thị tiến độ % thời gian thực.
4. **Bước 4 - Kiểm tra Preview & Điều chỉnh**:
   - Kiểm tra cột **"Tên Mới Dự Kiến"** trên bảng.
   - **Nhấp đúp chuột** vào hàng bất kỳ để xem ảnh phóng to và vị trí chữ được khoanh vùng.
   - Nếu ảnh có nhiều mã: **Chuột phải** → **"Chọn ứng viên khác (Candidates)..."** để chọn mã chính xác.
   - Hoặc chọn **"Nhập sửa mã thủ công..."** nếu muốn đặt tên theo ý muốn.
5. **Bước 5 - Đổi tên**: Bấm **"✏️ Thực Hiện Đổi Tên (Rename)"** để áp dụng thay đổi trên ổ đĩa.
6. **Bước 6 - Xuất Log CSV**: Bấm **"📊 Xuất Báo Cáo CSV"** để lưu lại lịch sử đối chiếu.

---

## 📦 Hướng Dẫn Đóng Gói Thành File .EXE (PyInstaller)

Tool đã tích hợp sẵn script đóng gói tự động `build_exe.py` đã kèm đầy đủ các gói dữ liệu và models:

```powershell
# 1. Kích hoạt venv (nếu chưa kích hoạt)
.\venv\Scripts\Activate.ps1

# 2. Chạy script đóng gói
python build_exe.py
```

Sau khi chạy xong, file thực thi sẽ nằm tại:
`dist\AI_OCR_Image_Renamer\AI_OCR_Image_Renamer.exe`

Bạn có thể tạo Shortcut ra Desktop hoặc nén thư mục `AI_OCR_Image_Renamer` gửi sang máy khác để chạy trực tiếp mà không cần cài Python!

---

## 🧪 Chạy Bộ Kiểm Thử Tự Động (Unit Tests)

Để kiểm tra độ ổn định của toàn bộ logic xử lý ảnh, trích xuất Regex, sửa nhầm ký tự và giải quyết va chạm tên:
```powershell
python tests/test_components.py
```
