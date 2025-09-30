import os
import subprocess
import concurrent.futures
from docx import Document
from typing import Dict

class ImageUtils:
    async def extract_and_convert_images(self, docx_path: str, image_dir: str) -> Dict[str, str]:
        doc = Document(docx_path)
        if not os.path.exists(image_dir):
            os.makedirs(image_dir)

        images_map = {}  # map original filename to final filename
        tasks = []  # list of (filepath, webp_path, filename)
        count = 1
        for rel in doc.part.rels.values():
            if "image" in rel.target_ref:
                image_part = rel._target
                ext = image_part.content_type.split("/")[-1]  # e.g., wmf, png, jpeg
                filename = f"image{count}.{ext}"
                filepath = os.path.join(image_dir, filename)

                # Write original image
                with open(filepath, "wb") as f:
                    f.write(image_part.blob)

                final_filename = filename
                if ext in ["wmf", "emf", "x-wmf"]:
                    webp_filename = filename.rsplit(".", 1)[0] + ".webp"
                    webp_path = os.path.join(image_dir, webp_filename)
                    tasks.append((filepath, webp_path, filename))
                else:
                    # For other formats, keep as is
                    pass

                images_map[filename] = final_filename
                count += 1

        # Multithreaded conversion
        def convert_task(filepath: str, webp_path: str) -> bool:
            try:
                subprocess.run(["magick", filepath, webp_path], check=True)
                return True
            except Exception as e:
                print(f"Convert error for {filepath}: {e}")
                return False

        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = list(executor.map(lambda t: convert_task(t[0], t[1]), tasks))

        for i, (filepath, webp_path, filename) in enumerate(tasks):
            if results[i]:
                final_filename = os.path.basename(webp_path)
                # Delete the original WMF file after successful conversion
                os.remove(filepath)
            else:
                final_filename = filename  # Keep original if failed
            images_map[filename] = final_filename

        return images_map