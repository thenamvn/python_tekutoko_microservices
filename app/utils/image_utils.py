import os
import subprocess
import concurrent.futures
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class ImageUtils:
    # File extensions that need LibreOffice for conversion (must be sequential)
    LIBREOFFICE_EXTENSIONS = {'.wmf', '.emf'}

    def _convert_wmf_to_webp(self, filepath: str, webp_path: str) -> bool:
        """
        Convert WMF/EMF files to WebP using wmf2gd (WMF→PNG) then magick (PNG→WebP).
        """
        try:
            outdir = os.path.dirname(filepath)
            base = os.path.splitext(os.path.basename(filepath))[0]
            ext = os.path.splitext(filepath)[1].lower()
            png_path = os.path.join(outdir, f"{base}.png")

            # Step 1: Convert WMF/EMF → PNG via wmf2gd
            result = subprocess.run(
                ["wmf2gd", "-o", png_path, filepath],
                check=True, capture_output=True, text=True, timeout=30
            )
            logger.info(f"wmf2gd converted {filepath} to PNG")

            if not os.path.exists(png_path):
                logger.error(f"wmf2gd did not produce PNG for {filepath}")
                return False

            # Step 2: Convert PNG → WebP via magick
            result = subprocess.run(
                ["magick", png_path, webp_path],
                check=True, capture_output=True, text=True, timeout=30
            )
            logger.info(f"Converted {png_path} to {webp_path}")

            # Clean up intermediate PNG
            try:
                os.remove(png_path)
            except OSError:
                pass

            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"WMF conversion failed for {filepath}: {e.stderr}")
            print(f"Lỗi chuyển đổi WMF {filepath}: {e}\nThông báo lỗi: {e.stderr}")
            return False
        except subprocess.TimeoutExpired:
            logger.error(f"WMF conversion timed out for {filepath}")
            print(f"Lỗi: Chuyển đổi WMF {filepath} quá thời gian.")
            return False
        except Exception as e:
            logger.error(f"Unexpected error converting WMF {filepath}: {e}")
            print(f"Lỗi không xác định khi chuyển đổi WMF {filepath}: {e}")
            return False

    def _convert_image_to_webp(self, filepath: str, webp_path: str) -> bool:
        """Convert non-WMF images to WebP using magick directly."""
        try:
            result = subprocess.run(
                ["magick", filepath, webp_path],
                check=True, capture_output=True, text=True, timeout=30
            )
            logger.info(f"Converted {filepath} to {webp_path}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Conversion failed for {filepath}: {e.stderr}")
            print(f"Lỗi chuyển đổi file {filepath}: {e}\nThông báo lỗi: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error converting {filepath}: {e}")
            print(f"Lỗi không xác định khi chuyển đổi {filepath}: {e}")
            return False

    def convert_extracted_images(self, image_dir: str = "media") -> Dict[str, str]:
        """
        Quét thư mục media, chuyển đổi TẤT CẢ các file ảnh sang định dạng WebP.
        WMF/EMF files use wmf2gd→magick pipeline. Others use magick directly.
        All conversions run in parallel.
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
            webp_filename = os.path.splitext(filename)[0] + ".webp"
            webp_path = os.path.join(image_dir, webp_filename)
            ext = os.path.splitext(filename)[1].lower()
            is_wmf = ext in self.LIBREOFFICE_EXTENSIONS
            tasks.append((filepath, webp_path, filename, is_wmf))

        def convert_one(filepath, webp_path, is_wmf):
            if is_wmf:
                return self._convert_wmf_to_webp(filepath, webp_path)
            else:
                return self._convert_image_to_webp(filepath, webp_path)

        # Run all conversions in parallel (wmf2gd is safe for parallel use)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = list(executor.map(
                lambda t: convert_one(t[0], t[1], t[3]),
                tasks
            ))

        # Collect results
        for i, (filepath, webp_path, original_filename, _) in enumerate(tasks):
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