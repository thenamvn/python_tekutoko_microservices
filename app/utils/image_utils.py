import os
import subprocess
import concurrent.futures
from typing import Dict

class ImageUtils:
    def convert_extracted_images(self, image_dir: str = "media") -> Dict[str, str]:
        """
        Quét thư mục media, chuyển đổi TẤT CẢ các file ảnh sang định dạng WebP.
        """
        if not os.path.exists(image_dir):
            print(f"Lỗi: Thư mục ảnh '{image_dir}' không tồn tại.")
            return {}

        images_map = {}
        tasks = []

        for filename in os.listdir(image_dir):
            filepath = os.path.join(image_dir, filename)
            if not os.path.isfile(filepath):
                continue
            
            # Chuyển đổi TẤT CẢ file thành WebP
            webp_filename = os.path.splitext(filename)[0] + ".webp"
            webp_path = os.path.join(image_dir, webp_filename)
            tasks.append((filepath, webp_path, filename))

        def convert_task(filepath, webp_path):
            """Hàm thực hiện chuyển đổi một file ảnh."""
            try:
                subprocess.run(
                    ["magick", filepath, webp_path], 
                    check=True, capture_output=True, text=True
                )
                return True
            except subprocess.CalledProcessError as e:
                print(f"Lỗi chuyển đổi file {filepath}: {e}\nThông báo lỗi: {e.stderr}")
                return False
            except Exception as e:
                print(f"Lỗi không xác định khi chuyển đổi {filepath}: {e}")
                return False

        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = list(executor.map(lambda t: convert_task(t[0], t[1]), tasks))

        for i, (filepath, webp_path, original_filename) in enumerate(tasks):
            if results[i]:
                final_filename = os.path.basename(webp_path)
                images_map[original_filename] = final_filename
                try:
                    os.remove(filepath)  # Xóa file gốc
                except OSError as e:
                    print(f"Không thể xóa file gốc {filepath}: {e}")
            else:
                # Nếu chuyển đổi thất bại, giữ file gốc
                images_map[original_filename] = original_filename

        return images_map