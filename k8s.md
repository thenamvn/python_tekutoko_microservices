Collecting workspace informationChào bạn, là **GitHub Copilot**. Tôi hiểu bạn đang muốn chuyển đổi từ một người chưa biết gì về Kubernetes (K8s) sang việc tự tay triển khai dự án DOCX Processor này. Đừng lo, đây là lộ trình phổ biến cho DevOps.

Dưới đây là hướng dẫn "Zero to Hero" chia thành từng bước cụ thể cho dự án của bạn.

---

### Phần 1: Các khái niệm cơ bản (Cho người mới bắt đầu)

Trước khi gõ lệnh, bạn cần hiểu 4 từ khóa cốt lõi trong K8s:

1.  **Pod**: Đơn vị nhỏ nhất. Hãy tưởng tượng nó là một cái "hộp" bao bọc lấy Docker Container của bạn. 1 Pod = 1 (hoặc vài) container chạy ứng dụng main.py.
2.  **Deployment**: Người quản lý. Bạn không tạo Pod trực tiếp, bạn bảo Deployment: "Hãy chạy cho tôi 3 bản sao (replicas) của app này". Nếu 1 cái chết, Deployment sẽ tự tạo lại cái mới.
3.  **Service**: Cổng giao tiếp. Pod có địa chỉ IP thay đổi liên tục (khi khởi động lại). Service cung cấp một địa chỉ IP cố định để các service khác gọi vào `api/v1/process-docx`.
4.  **PersistentVolumeClaim (PVC)**: Ổ cứng lưu trữ. Vì dự án của bạn lưu file vào thư mục outputs, nếu Pod bị xóa, dữ liệu mất theo. PVC giúp dữ liệu tồn tại vĩnh viễn dù Pod có bị hủy.

---

### Phần 2: Cài đặt môi trường (Localhost)

Vì bạn đang dùng Windows (thấy ổ đĩa d:), cách nhanh nhất để có K8s là dùng **Docker Desktop**.

1.  Cài đặt **Docker Desktop** bản mới nhất.
2.  Mở Docker Desktop -> **Settings** (bánh răng) -> **Kubernetes**.
3.  Tích vào **Enable Kubernetes** -> Apply & Restart.
4.  Cài đặt xong, mở Terminal (CMD/PowerShell) gõ: `kubectl version`. Nếu hiện thông tin là thành công.

---

### Phần 3: Chuẩn hóa Container (Quan trọng)

Dự án của bạn cần `pandoc` và `imagemagick`. Trong thư mục code tôi thấy file `.msi` (Windows installer), nhưng K8s chạy Linux, nên ta phải sửa Dockerfile để cài thư viện Linux.

**File:** Dockerfile (Cập nhật file này ở thư mục gốc)
```dockerfile
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
```

**Build Image:**
Mở terminal tại thư mục gốc dự án và chạy:
```bash
docker build -t docx-processor:v1 .
```

---

### Phần 4: Viết file cấu hình K8s (Manifests)

Hãy tạo một thư mục tên là `k8s` trong dự án. Chúng ta sẽ tạo 3 file YAML.

1.  **Lưu trữ dữ liệu (`k8s/1-storage.yaml`)**:
    Để giữ lại thư mục outputs khi update code.

File: "k8s/1-storage.yaml"
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: docx-output-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
```

2.  **Triển khai ứng dụng (`k8s/2-deployment.yaml`)**:
    Định nghĩa cách chạy app, biến môi trường (Database), và gắn ổ cứng.

File: "k8s/2-deployment.yaml"
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: docx-processor-deploy
spec:
  replicas: 1 # Số lượng bản sao (có thể tăng lên 2, 3 để chịu tải)
  selector:
    matchLabels:
      app: docx-processor
  template:
    metadata:
      labels:
        app: docx-processor
    spec:
      containers:
      - name: docx-processor
        image: docx-processor:v1 # Image ta vừa build
        imagePullPolicy: IfNotPresent # Dùng image local, không tải từ mạng
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          value: "mysql+pymysql://root:password@host.docker.internal:3306/tekutoko" # Ví dụ kết nối DB localhost
        - name: BASE_URL
          value: "http://localhost:30000"
        volumeMounts:
        - mountPath: /app/outputs # Đường dẫn trong container
          name: output-storage
      volumes:
      - name: output-storage
        persistentVolumeClaim:
          claimName: docx-output-pvc
```

3.  **Mở cổng mạng (`k8s/3-service.yaml`)**:
    Giúp bạn truy cập được API từ bên ngoài.

File: "k8s/3-service.yaml"
```yaml
apiVersion: v1
kind: Service
metadata:
  name: docx-processor-service
spec:
  type: NodePort # Dùng NodePort để test local dễ dàng
  selector:
    app: docx-processor
  ports:
    - protocol: TCP
      port: 8000      # Port của Service
      targetPort: 8000 # Port của Container
      nodePort: 30000 # Port bạn sẽ truy cập từ trình duyệt (localhost:30000)
```

---

### Phần 5: Triển khai (Deploy)

Bây giờ hãy chạy các lệnh sau trong Terminal:

1.  **Áp dụng cấu hình:**
    ```bash
    kubectl apply -f k8s/
    ```
    *Lệnh này sẽ tạo PVC, Deployment và Service cùng lúc.*

2.  **Kiểm tra trạng thái:**
    ```bash
    kubectl get pods
    ```
    *Bạn sẽ thấy trạng thái `ContainerCreating` rồi chuyển sang `Running`.*

3.  **Xem logs (nếu có lỗi):**
    ```bash
    kubectl logs -f deployment/docx-processor-deploy
    ```

---

### Phần 6: Kiểm tra kết quả

Sau khi Pod đã `Running`, bạn có thể truy cập Swagger UI tại:
**http://localhost:30000/docs**

Nếu bạn upload file qua API đó, file sẽ được xử lý, lưu vào Volume và không bị mất đi kể cả khi bạn xóa Pod.

### Tóm tắt lộ trình tiếp theo:
1.  Hiện tại DB đang để hardcode, sau này nên dùng `Secret` (k8s object) để bảo mật mật khẩu.
2.  Sau này khi deploy lên server thật (AWS/Google/VPS riêng), bạn sẽ đổi Service type từ `NodePort` sang `LoadBalancer` hoặc dùng `Ingress`.