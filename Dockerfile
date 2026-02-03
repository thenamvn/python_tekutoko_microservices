# Sử dụng Python 3.9 bản slim (nhẹ)
FROM python:3.9-slim

# Thiết lập thư mục làm việc
WORKDIR /app

# 1. Cài đặt các thư viện hệ thống cần thiết (Pandoc, ImageMagick cho Linux)
RUN apt-get update && apt-get install -y \
    pandoc \
    imagemagick \
    && rm -rf /var/lib/apt/lists/*

# Chỉnh sửa policy của ImageMagick để cho phép convert PDF/DOCX (thường bị chặn mặc định)
RUN sed -i 's/<policy domain="coder" rights="none" pattern="PDF" \/>/<policy domain="coder" rights="read|write" pattern="PDF" \/>/g' /etc/ImageMagick-6/policy.xml

# 2. Copy requirements và cài đặt thư viện Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy toàn bộ code vào
COPY . .

# Tạo thư mục outputs để tránh lỗi permission
RUN mkdir -p outputs

# 4. Expose port 8000
EXPOSE 8000

# 5. Lệnh chạy app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]