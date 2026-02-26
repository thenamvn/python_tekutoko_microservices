# Debug Docker Image Conversion Issues

## Các thay đổi đã thực hiện

### 1. Cập nhật Dockerfile
- ✅ Thêm `ghostscript` và `libwmf-bin` để hỗ trợ chuyển đổi WMF
- ✅ Cập nhật policy cho cả PDF, PS, EPS, XPS (cần cho WMF)
- ✅ Hỗ trợ cả ImageMagick 6 và 7

### 2. Sửa `split_blocks()` trong `docx_service.py`
- ✅ Xử lý đường dẫn tuyệt đối từ Pandoc (VD: `outputs/uuid/media/image3.wmf`)
- ✅ Chỉ lấy filename cuối cùng (basename)
- ✅ Pattern regex mở rộng để bắt cả path có và không có `[options]`

### 3. Thêm logging vào `image_utils.py`
- ✅ Log mỗi bước convert để dễ debug
- ✅ Lưu file gốc nếu convert thất bại

### 4. Thêm fsync vào `docx_service.py`
- ✅ Đảm bảo file JSON được ghi hoàn toàn trước khi return

---

## Cách rebuild và test

### Bước 1: Rebuild image
```bash
# Build image mới
docker build -t docx-processor:v2 .

# Hoặc nếu dùng docker-compose
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Bước 2: Kiểm tra ImageMagick trong container
```bash
# Vào container
docker exec -it <container_name> bash

# Kiểm tra version
magick --version

# Test convert WMF sang WebP
cd outputs/<uuid>/media/
magick image1.wmf test.webp
ls -lah
```

### Bước 3: Xem logs
```bash
# Xem logs real-time
docker logs -f <container_name>

# Hoặc với docker-compose
docker-compose logs -f
```

### Bước 4: Test API
```bash
# Upload file DOCX
curl -X POST "https://tekutoko.duckdns.org/api/v1/process-docx" \
  -F "file=@test.docx" \
  -F "username=test@example.com" \
  -F "title=Test Exam"

# Lấy kết quả (UUID từ response trên)
curl -X GET "https://tekutoko.duckdns.org/api/v1/quiz/<UUID>"
```

---

## Các vấn đề thường gặp

### 1. Ảnh vẫn là .wmf thay vì .webp
**Nguyên nhân:** ImageMagick không chạy được hoặc thiếu ghostscript

**Giải pháp:**
```bash
# Vào container kiểm tra
docker exec -it <container> bash
apt-get update
apt-get install -y ghostscript libwmf-bin
```

### 2. Response trả về `\includegraphics{...}` thay vì tách blocks
**Nguyên nhân:** Regex không bắt được đường dẫn tuyệt đối

**Đã fix:** Pattern mới trong `split_blocks()` xử lý cả relative và absolute paths

### 3. 404 Not Found không ổn định
**Nguyên nhân:** File JSON chưa được flush/sync hoàn toàn

**Đã fix:** Thêm `f.flush()` và `os.fsync()` sau khi ghi JSON

### 4. Database connection timeout
**Giải pháp:** Kiểm tra DATABASE_URL trong docker-compose.yml
```yaml
environment:
  - DATABASE_URL=mysql+pymysql://user:pass@mysql:3306/dbname
```

---

## Kiểm tra kết quả đúng

Response phải có dạng:
```json
{
  "exam_uuid": "...",
  "questions": [
    {
      "id": 1,
      "blocks": [
        {
          "type": "text",
          "content": "Câu hỏi text"
        },
        {
          "type": "image",
          "src": "https://tekutoko.duckdns.org/outputs/uuid/media/image1.webp"
        }
      ],
      "options": [...]
    }
  ]
}
```

**Sai nếu:**
- ❌ `"content": "\\includegraphics{...}"`
- ❌ `"src": "outputs/uuid/media/image.wmf"`
- ❌ Không có blocks riêng cho image

**Đúng nếu:**
- ✅ Image tách thành block riêng với `type: "image"`
- ✅ `src` trỏ đến file `.webp`
- ✅ URL đầy đủ có BASE_URL

---

## Logs cần xem

Khi upload file, logs phải hiện:
```
INFO: Starting image conversion in outputs/<uuid>/media
INFO: Processing image: image1.wmf
INFO: Converted outputs/<uuid>/media/image1.wmf to outputs/<uuid>/media/image1.webp
INFO: Deleted original file: outputs/<uuid>/media/image1.wmf
```

Nếu thấy lỗi:
```
ERROR: Conversion failed for ...: <error message>
```
→ Vào container chạy lệnh `magick` thủ công để debug.
