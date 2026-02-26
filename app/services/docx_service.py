from pydantic import BaseModel
from typing import List, Optional, Dict
import json
import os
import re
import pypandoc
import shutil
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
        
        temp_docx_path = os.path.join(output_dir, "temp.docx")
        async with aiofiles.open(temp_docx_path, 'wb') as f:
            content = await file.read()
            await f.write(content)

        tex_path = os.path.join(output_dir, "temp.tex")
        latex_content = self.convert_docx_to_latex(temp_docx_path, tex_path, output_dir)

        # Đường dẫn thư mục media sẽ được tạo bởi pandoc
        image_dir = os.path.join(output_dir, "media")
        
        if os.path.exists(image_dir):
            images_map = self.image_utils.convert_extracted_images(image_dir)
        else:
            images_map = {}

        questions = self.parse_latex_to_json(latex_content)

        self.update_image_srcs(questions, images_map, request_uuid)

        json_path = os.path.join(output_dir, "output.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"questions": [q.dict() for q in questions]}, f, ensure_ascii=False, indent=4)
            f.flush()  # Force write to disk
            os.fsync(f.fileno())  # Ensure data is written

        os.remove(temp_docx_path)
        if os.path.exists(tex_path):
            os.remove(tex_path)

        return ProcessResponse(questions=questions)

    def convert_docx_to_latex(self, docx_path: str, output_tex_path: str, output_dir: str) -> str:
        try:
            # Xóa thư mục media cũ nếu tồn tại
            media_dir = os.path.join(output_dir, "media")
            if os.path.exists(media_dir):
                shutil.rmtree(media_dir)
            
            # Sử dụng output_dir làm base directory cho extract-media
            extra_args = [f'--extract-media={output_dir}', '--wrap=none']
            pypandoc.convert_file(docx_path, 'latex', outputfile=output_tex_path, extra_args=extra_args)
            with open(output_tex_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise Exception(f"Error converting DOCX to LaTeX: {e}")

    def split_blocks(self, text: str) -> List[Dict]:
        blocks = []
        # Clean up pandoc artefacts
        text = text.replace(r'\pandocbounded{', '')

        # Updated pattern to handle both relative and absolute paths
        pattern = re.compile(
            r'\\includegraphics(?:\[.*?\])?\{([^}]+?)\}'  # Capture any path (relative or absolute)
            r'|(\$.*?\$|\\\(.+?\\\)|\\\[.+?\\\])',  # math
            re.DOTALL
        )
        last = 0
        for m in pattern.finditer(text):
            start, end = m.span()
            if start > last:
                txt = text[last:start].strip()
                if txt.endswith('}') and not txt.count('{') > txt.count('}'): 
                     txt = txt[:-1]

                if txt:
                    blocks.append({"type": "text", "content": txt})
            if m.group(1):  # image
                # Extract only the filename, remove full path
                image_path = m.group(1).replace('./', '')
                # Handle absolute paths like "outputs/uuid/media/imageX.wmf"
                if '/' in image_path:
                    # Extract only filename (last part after /)
                    basename = os.path.basename(image_path)
                else:
                    basename = image_path
                blocks.append({"type": "image", "src": basename})
            elif m.group(2):  # math
                blocks.append({"type": "math", "content": m.group(2)})
            last = end
        if last < len(text):
            txt = text[last:].strip()
            if txt.endswith('}') and not txt.count('{') > txt.count('}'): 
                 txt = txt[:-1]
            if txt:
                blocks.append({"type": "text", "content": txt})
        return blocks

    def parse_latex_to_json(self, latex_content: str) -> List[Question]:
        # Cải thiện regex split để bắt được "Câu 1." hoặc "Câu 1:"
        # Chấp nhận có thể được bọc trong \textbf{} hoặc không
        # Pattern: (StartBold)? Câu <space> <digit> <dot/colon> (EndBold)?
        question_blocks = re.split(r'(?:\\textbf\{)?Câu\s+\d+[\.:](?:\})?', latex_content)[1:]
        questions = []

        # Regex tìm đáp án đầu tiên (A. B. C. D.)
        # Chấp nhận các format: \textbf{A.}, \ul{A.}, \textbf{\ul{A.}}
        # Ta dùng pattern đơn giản hóa: (các thẻ mở)* ([A-D])\. (các thẻ đóng)*
        # Tuy nhiên để an toàn, ta tìm kiếm pattern cốt lõi "A." được bọc hoặc không
        first_option_pattern = re.compile(r'(?:\\textbf\{|\\ul\{|\\underline\{)*([A-D])\.(?:\})*')

        # Regex split options
        options_split_pattern = re.compile(
            r'(?:\\textbf\{|\\ul\{|\\underline\{)*([A-D])\.(?:\})*(.*?)(?=(?:\\textbf\{|\\ul\{|\\underline\{)*[A-D]\.(?:\})*|\Z)', 
            re.DOTALL
        )

        for idx, block in enumerate(question_blocks, 1):
            # 1. Xóa các nhiễu format
            clean_block = block.replace(r'\begin{quote}', '').replace(r'\end{quote}', '')
            clean_block = clean_block.replace(r'\begin{enumerate}', '').replace(r'\end{enumerate}', '')
            clean_block = clean_block.replace(r'\item', '')

            # 2. Tìm vị trí xuất hiện đáp án đầu tiên
            match = first_option_pattern.search(clean_block)
            
            if match:
                start_index = match.start()
                question_text = clean_block[:start_index].strip()
                options_block = clean_block[start_index:]
            else:
                question_text = clean_block.strip()
                options_block = ""

            blocks = self.split_blocks(question_text)

            options = []
            correct = None
            
            # 3. Quét các đáp án
            for m in options_split_pattern.finditer(options_block):
                # Group 1: Label (A, B, C, D)
                label = m.group(1) 
                # Group 2: Content
                opt_content = m.group(2).strip()
                
                # Check formatted (đơn giản là có label tức là có option)
                is_correct = False
                # Logic check correct cũ dựa vào group capture của \ul, giờ ko chắc chắn.
                # Nếu muốn check correct: thường là đáp án có gạch chân (\ul hoặc \underline)
                # Ta check trong chuỗi gốc match group 0 xem có chứa \ul hay \underline không
                full_match = m.group(0) # bao gồm cả label và format prefix
                # Lấy phần prefix trước label
                prefix = full_match.split(label + '.')[0]
                if r'\ul' in prefix or r'\underline' in prefix:
                     is_correct = True

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

    def update_image_srcs(self, questions: List[Question], images_map: Dict[str, str], request_uuid: str):
        for question in questions:
            for block in question.blocks:
                if block.type == "image" and block.src:
                    original_filename = block.src
                    if original_filename in images_map:
                        new_filename = images_map[original_filename]
                        block.src = f"{self.base_url}/outputs/{request_uuid}/media/{new_filename}"
                    else:
                        block.src = f"{self.base_url}/outputs/{request_uuid}/media/{original_filename}"
            
            for option in question.options:
                for block in option.blocks:
                    if block.type == "image" and block.src:
                        original_filename = block.src
                        if original_filename in images_map:
                            new_filename = images_map[original_filename]
                            block.src = f"{self.base_url}/outputs/{request_uuid}/media/{new_filename}"
                        else:
                            block.src = f"{self.base_url}/outputs/{request_uuid}/media/{original_filename}"