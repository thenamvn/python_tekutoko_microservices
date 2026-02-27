import os
import sys
import re
import subprocess
import concurrent.futures
import logging
import tempfile
import shutil
from typing import Dict

logger = logging.getLogger(__name__)

IS_WINDOWS = sys.platform == "win32"

class ImageUtils:
    def convert_extracted_images(self, image_dir: str = "media") -> Dict[str, str]:
        """
        Quét thư mục media, chuyển đổi TẤT CẢ các file ảnh sang định dạng WebP.
        """
        if not os.path.exists(image_dir):
            logger.error(f"Image directory does not exist: {image_dir}")
            print(f"Lỗi: Thư mục ảnh '{image_dir}' không tồn tại.")
            return {}

        logger.info(f"Starting image conversion in {image_dir}")
        images_map = {}
        tasks = []

        for filename in os.listdir(image_dir):
            filepath = os.path.join(image_dir, filename)
            if not os.path.isfile(filepath):
                continue
            
            logger.info(f"Processing image: {filename}")
            # Chuyển đổi TẤT CẢ file thành WebP
            webp_filename = os.path.splitext(filename)[0] + ".webp"
            webp_path = os.path.join(image_dir, webp_filename)
            tasks.append((filepath, webp_path, filename))

        def convert_task(filepath, webp_path):
            """Hàm thực hiện chuyển đổi một file ảnh."""
            try:
                ext = os.path.splitext(filepath)[1].lower()

                if IS_WINDOWS:
                    # Windows: dùng ImageMagick 7 (magick), hỗ trợ WMF native qua GDI
                    if ext in ['.wmf', '.emf']:
                        subprocess.run(
                            [
                                "magick",
                                "-density", "300",
                                filepath,
                                "-background", "white",
                                "-alpha", "remove",
                                "-quality", "90",
                                webp_path
                            ],
                            check=True, capture_output=True, text=True, timeout=60
                        )
                    else:
                        subprocess.run(
                            ["magick", filepath, "-quality", "90", webp_path],
                            check=True, capture_output=True, text=True, timeout=30
                        )
                else:
                    # Linux (Docker): IM6 dùng `convert`, WMF đi qua wmf2svg + rsvg-convert
                    if ext in ['.wmf', '.emf']:
                        tmp_dir = tempfile.mkdtemp()
                        try:
                            base = os.path.splitext(os.path.basename(filepath))[0]
                            svg_path = os.path.join(tmp_dir, base + ".svg")

                            # Bước 1: WMF → SVG (wmf2svg từ libwmf-bin)
                            r1 = subprocess.run(
                                ["wmf2svg", "-o", svg_path, filepath],
                                capture_output=True, timeout=30
                            )
                            if not os.path.exists(svg_path):
                                logger.error(f"wmf2svg failed for {filepath}: {r1.stderr}")
                                return False

                            # Fix encoding: wmf2svg có thể tạo SVG với bytes không phải UTF-8
                            # Đọc bằng latin-1 (chấp nhận mọi byte), ghi lại thành UTF-8
                            with open(svg_path, 'rb') as f:
                                raw_bytes = f.read()
                            svg_text = raw_bytes.decode('latin-1')
                            if svg_text.startswith('<?xml'):
                                svg_text = re.sub(
                                    r"<\?xml[^?]*\?>",
                                    '<?xml version="1.0" encoding="UTF-8"?>',
                                    svg_text, count=1
                                )
                            else:
                                svg_text = '<?xml version="1.0" encoding="UTF-8"?>\n' + svg_text
                            with open(svg_path, 'w', encoding='utf-8') as f:
                                f.write(svg_text)

                            # Bước 2: SVG → PNG (rsvg-convert từ librsvg2-bin)
                            png_path = os.path.join(tmp_dir, base + ".png")
                            subprocess.run(
                                [
                                    "rsvg-convert",
                                    "--width", "2000",
                                    "--keep-aspect-ratio",
                                    "--background-color", "white",
                                    "--format", "png",
                                    "--output", png_path,
                                    svg_path
                                ],
                                check=True, capture_output=True, text=True, timeout=30
                            )

                            # Bước 3: PNG → WebP (convert từ imagemagick)
                            subprocess.run(
                                ["convert", png_path, "-quality", "90", webp_path],
                                check=True, capture_output=True, text=True, timeout=30
                            )
                            logger.info(f"Converted {filepath} → {webp_path} via wmf2svg+rsvg-convert")
                            return True
                        finally:
                            shutil.rmtree(tmp_dir, ignore_errors=True)
                    else:
                        subprocess.run(
                            ["convert", filepath, "-quality", "90", webp_path],
                            check=True, capture_output=True, text=True, timeout=30
                        )

                logger.info(f"Converted {filepath} to {webp_path}")
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"Conversion failed for {filepath}: {e.stderr}")
                print(f"Lỗi chuyển đổi file {filepath}: {e}\nThông báo lỗi: {e.stderr}")
                return False
            except subprocess.TimeoutExpired:
                logger.error(f"Conversion timeout for {filepath}")
                print(f"Lỗi: Chuyển đổi {filepath} quá thời gian.")
                return False
            except Exception as e:
                logger.error(f"Unexpected error converting {filepath}: {e}")
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
                    logger.info(f"Deleted original file: {filepath}")
                except OSError as e:
                    logger.warning(f"Could not delete original file {filepath}: {e}")
                    print(f"Không thể xóa file gốc {filepath}: {e}")
            else:
                # Nếu chuyển đổi thất bại, giữ file gốc
                images_map[original_filename] = original_filename
                logger.warning(f"Kept original file due to conversion failure: {original_filename}")

        return images_map