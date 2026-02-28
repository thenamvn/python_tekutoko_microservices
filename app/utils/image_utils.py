import concurrent.futures
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

IS_WINDOWS = sys.platform == "win32"

# soffice xuất PNG ở 96 DPI mặc định.
# Upscale lên 3x (= ~288 DPI equivalent) để text/ký hiệu toán sắc nét.
_SOFFICE_UPSCALE = "300%"


class ImageUtils:
    def convert_extracted_images(self, image_dir: str = "media") -> Dict[str, str]:
        if not os.path.exists(image_dir):
            logger.error("Image directory does not exist: %s", image_dir)
            return {}

        images_map: Dict[str, str] = {}
        tasks: List[Tuple[str, str, str]] = []

        for filename in os.listdir(image_dir):
            filepath = os.path.join(image_dir, filename)
            if not os.path.isfile(filepath):
                continue
            webp_filename = f"{os.path.splitext(filename)[0]}.webp"
            webp_path = os.path.join(image_dir, webp_filename)
            tasks.append((filepath, webp_path, filename))

        def _convert_wmf_with_soffice(filepath: str, webp_path: str) -> bool:
            tmp_dir = tempfile.mkdtemp(prefix="lo_")
            try:
                base_name = os.path.splitext(os.path.basename(filepath))[0]
                png_path = os.path.join(tmp_dir, f"{base_name}.png")

                profile_dir = os.path.join(tmp_dir, "profile")
                os.makedirs(profile_dir, exist_ok=True)

                env = os.environ.copy()
                env["HOME"] = tmp_dir
                env["JAVA_HOME"] = "/usr/lib/jvm/default-java"
                env["JRE_HOME"] = "/usr/lib/jvm/default-java"
                env["PATH"] = f"{env.get('PATH', '')}:/usr/lib/jvm/default-java/bin"

                user_installation = f"-env:UserInstallation=file://{profile_dir}"

                result = subprocess.run(
                    [
                        "soffice",
                        "--headless",
                        "--invisible",
                        "--nologo",
                        "--nodefault",
                        "--nofirststartwizard",
                        "--norestore",
                        user_installation,
                        "--convert-to",
                        "png",
                        "--outdir",
                        tmp_dir,
                        filepath,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=90,
                    env=env,
                )

                if not os.path.exists(png_path):
                    logger.error(
                        "soffice conversion failed for %s.\nstdout: %s\nstderr: %s",
                        filepath,
                        result.stdout,
                        result.stderr,
                    )
                    return False

                subprocess.run(
                    [
                        "convert",
                        png_path,
                        # Trim canvas thừa của soffice
                        "-trim",
                        "+repage",
                        # Upscale 3x với Lanczos (tốt nhất cho text/line art)
                        # soffice xuất 96 DPI → sau upscale ~288 DPI
                        "-filter", "Lanczos",
                        "-resize", _SOFFICE_UPSCALE,
                        # Sharpen nhẹ sau upscale để text sắc nét hơn
                        "-unsharp", "0x1+0.5+0",
                        # Padding nhỏ
                        "-bordercolor", "white",
                        "-border", "12",
                        # Lossless WebP để không mất chất lượng
                        "-define", "webp:lossless=true",
                        "-quality", "100",
                        webp_path,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                return True

            except subprocess.CalledProcessError as exc:
                logger.error("ImageMagick conversion failed for %s: %s", filepath, exc.stderr)
                return False
            except subprocess.TimeoutExpired:
                logger.error("soffice conversion timeout for %s", filepath)
                return False
            except Exception as exc:
                logger.error("Unexpected soffice conversion error for %s: %s", filepath, exc)
                return False
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        def convert_task(filepath: str, webp_path: str) -> bool:
            ext = os.path.splitext(filepath)[1].lower()
            try:
                if IS_WINDOWS:
                    if ext in [".wmf", ".emf"]:
                        cmd = [
                            "magick",
                            # density cao để render vector WMF sắc nét
                            "-density", "300",
                            filepath,
                            "-trim",
                            "+repage",
                            "-filter", "Lanczos",
                            "-resize", "200%",
                            "-unsharp", "0x1+0.5+0",
                            "-bordercolor", "white",
                            "-border", "12",
                            "-alpha", "remove",
                            "-define", "webp:lossless=true",
                            "-quality", "100",
                            webp_path,
                        ]
                    else:
                        cmd = [
                            "magick",
                            filepath,
                            "-define", "webp:lossless=true",
                            "-quality", "100",
                            webp_path,
                        ]
                    subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=90)
                    return True

                if ext in [".wmf", ".emf"]:
                    return _convert_wmf_with_soffice(filepath, webp_path)

                # PNG/JPG/GIF → WebP lossless
                subprocess.run(
                    [
                        "convert",
                        filepath,
                        "-define", "webp:lossless=true",
                        "-quality", "100",
                        webp_path,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=40,
                )
                return True

            except subprocess.CalledProcessError as exc:
                logger.error("Conversion failed for %s: %s", filepath, exc.stderr)
                return False
            except subprocess.TimeoutExpired:
                logger.error("Conversion timeout for %s", filepath)
                return False
            except Exception as exc:
                logger.error("Unexpected conversion error for %s: %s", filepath, exc)
                return False

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(lambda t: convert_task(t[0], t[1]), tasks))

        for i, (filepath, webp_path, original_filename) in enumerate(tasks):
            if results[i]:
                images_map[original_filename] = os.path.basename(webp_path)
                try:
                    os.remove(filepath)
                except OSError as exc:
                    logger.warning("Could not delete original file %s: %s", filepath, exc)
            else:
                images_map[original_filename] = original_filename
                logger.warning("Kept original file due to conversion failure: %s", original_filename)

        return images_map