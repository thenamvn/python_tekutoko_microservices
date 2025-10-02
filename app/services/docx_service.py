from pydantic import BaseModel
from typing import List, Optional, Dict
import json
import os
import re
import pypandoc
from docx import Document
import aiofiles
from fastapi import UploadFile
from app.utils.image_utils import ImageUtils

class Block(BaseModel):
    type: str
    content: Optional[str] = None
    src: Optional[str] = None

class Option(BaseModel):
    label: str
    blocks: List[Block]

class Question(BaseModel):
    id: int
    blocks: List[Block]
    options: List[Option]
    correct: Optional[str] = None

class ProcessResponse(BaseModel):
    questions: List[Question]

class DocxService:
    def __init__(self):
        self.image_utils = ImageUtils()
        self.base_url = os.getenv("BASE_URL", "http://localhost:8000")

    async def process_docx(self, file: UploadFile, request_uuid: str) -> ProcessResponse:
        output_dir = os.path.join("outputs", request_uuid)
        os.makedirs(output_dir, exist_ok=True)
        image_dir = os.path.join(output_dir, "media")
        os.makedirs(image_dir, exist_ok=True)

        temp_docx_path = os.path.join(output_dir, "temp.docx")
        async with aiofiles.open(temp_docx_path, 'wb') as f:
            content = await file.read()
            await f.write(content)

        images_map = await self.image_utils.extract_and_convert_images(temp_docx_path, image_dir)

        tex_path = os.path.join(output_dir, "temp.tex")
        latex_content = self.convert_docx_to_latex(temp_docx_path, tex_path)

        questions = self.parse_latex_to_json(latex_content)

        self.update_image_srcs(questions, images_map, image_dir, request_uuid)

        json_path = os.path.join(output_dir, "output.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"questions": [q.dict() for q in questions]}, f, ensure_ascii=False, indent=4)

        os.remove(temp_docx_path)
        if os.path.exists(tex_path):
            os.remove(tex_path)

        return ProcessResponse(questions=questions)

    def convert_docx_to_latex(self, docx_path: str, output_tex_path: str) -> str:
        try:
            pypandoc.convert_file(docx_path, 'latex', outputfile=output_tex_path)
            with open(output_tex_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise Exception(f"Error converting DOCX to LaTeX: {e}")

    def split_blocks(self, text: str) -> List[Dict]:
        blocks = []
        pattern = re.compile(
            r'\\includegraphics\[.*?\]\{(.*?)\}'  # image
            r'|(\$.*?\$|\\\(.+?\\\)|\\\[.+?\\\])'  # math
        )
        last = 0
        for m in pattern.finditer(text):
            start, end = m.span()
            if start > last:
                txt = text[last:start].strip()
                if txt:
                    blocks.append({"type": "text", "content": txt})
            if m.group(1):  # image
                blocks.append({"type": "image", "src": m.group(1)})
            elif m.group(2):  # math
                blocks.append({"type": "math", "content": m.group(2)})
            last = end
        if last < len(text):
            txt = text[last:].strip()
            if txt:
                blocks.append({"type": "text", "content": txt})
        return blocks

    def parse_latex_to_json(self, latex_content: str) -> List[Question]:
        question_blocks = re.split(r'\\textbf\{Câu \d+\:\}', latex_content)[1:]
        questions = []

        for idx, block in enumerate(question_blocks, 1):
            parts = re.split(r'\\begin\{quote\}', block, maxsplit=1)
            question_text = parts[0].strip()
            options_block = parts[1].split(r'\\end{quote}')[0] if len(parts) > 1 else ""

            blocks = self.split_blocks(question_text)

            option_pattern = re.compile(
                r'\\textbf\{(\\ul\{)?([A-D])\.}(.*?)(?=(?:\\textbf|\Z))', re.DOTALL)
            options = []
            correct = None
            for m in option_pattern.finditer(options_block):
                is_correct = m.group(1) is not None
                label = m.group(2)
                opt_content = m.group(3).replace('\n', ' ').strip(' .')
                opt_blocks = self.split_blocks(opt_content)
                options.append(Option(label=label, blocks=opt_blocks))
                if is_correct:
                    correct = label

            questions.append(Question(
                id=idx,
                blocks=blocks,
                options=options,
                correct=correct
            ))

        return questions

    def update_image_srcs(self, questions: List[Question], images_map: Dict[str, str], image_dir: str, request_uuid: str):
        for question in questions:
            for block in question.blocks:
                if block.type == "image" and block.src:
                    basename = os.path.basename(block.src)
                    # Prefer webp if exists
                    for ext in (".wmf", ".emf", ".x-wmf", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"):
                        if basename.endswith(ext):
                            webp_basename = basename.replace(ext, ".webp")
                            webp_path = os.path.join(image_dir, webp_basename)
                            if os.path.exists(webp_path):
                                block.src = f"{self.base_url}/outputs/{request_uuid}/media/{webp_basename}"
                                break
                    else:
                        if basename in images_map:
                            block.src = f"{self.base_url}/outputs/{request_uuid}/media/{images_map[basename]}"
            for option in question.options:
                for block in option.blocks:
                    if block.type == "image" and block.src:
                        basename = os.path.basename(block.src)
                        for ext in (".wmf", ".emf", ".x-wmf", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"):
                            if basename.endswith(ext):
                                webp_basename = basename.replace(ext, ".webp")
                                webp_path = os.path.join(image_dir, webp_basename)
                                if os.path.exists(webp_path):
                                    block.src = f"{self.base_url}/outputs/{request_uuid}/media/{webp_basename}"
                                    break
                        else:
                            if basename in images_map:
                                block.src = f"{self.base_url}/outputs/{request_uuid}/media/{images_map[basename]}"