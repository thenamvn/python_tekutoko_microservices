import json
import os
import re
import pypandoc
import subprocess
from docx import Document
import concurrent.futures

def extract_and_convert_images(docx_path, image_dir="media"):
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
            filename = f"image{count}.{ext}"  # Removed underscore to match pandoc naming
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
                # For other formats, optionally convert to webp if desired
                # For now, keep as is
                pass

            images_map[filename] = final_filename
            count += 1

    # Multithreaded conversion
    def convert_task(filepath, webp_path):
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

def convert_docx_to_latex(docx_path, output_tex_path):
    """
    Convert DOCX -> LaTeX using pandoc
    """
    try:
        pypandoc.convert_file(docx_path, 'latex', outputfile=output_tex_path)
        with open(output_tex_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error converting DOCX to LaTeX: {e}")
        return ""

def split_blocks(text):
    """
    Split text into blocks: text / image / math
    """
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

def parse_latex_to_json(latex_content):
    """
    Parse LaTeX into JSON: questions + options
    """
    question_blocks = re.split(r'\\textbf\{Câu \d+\:\}', latex_content)[1:]
    questions = []

    for idx, block in enumerate(question_blocks, 1):
        parts = re.split(r'\\begin\{quote\}', block, maxsplit=1)
        question_text = parts[0].strip()
        options_block = parts[1].split(r'\\end{quote}')[0] if len(parts) > 1 else ""

        blocks = split_blocks(question_text)

        option_pattern = re.compile(
            r'\\textbf\{(\\ul\{)?([A-D])\.}(.*?)(?=(?:\\textbf|\Z))', re.DOTALL)
        options = []
        correct = None
        for m in option_pattern.finditer(options_block):
            is_correct = m.group(1) is not None
            label = m.group(2)
            opt_content = m.group(3).replace('\n', ' ').strip(' .')
            opt_blocks = split_blocks(opt_content)
            options.append({"label": label, "blocks": opt_blocks})
            if is_correct:
                correct = label

        questions.append({
            "id": idx,
            "blocks": blocks,
            "options": options,
            "correct": correct
        })

    return questions

def update_image_srcs(questions, images_map, image_dir="media"):
    """
    Update image src in blocks to use converted WebP paths
    """
    for question in questions:
        for block in question["blocks"]:
            if block["type"] == "image":
                basename = os.path.basename(block["src"])
                if basename in images_map:
                    block["src"] = os.path.join(image_dir, images_map[basename])
                elif basename.endswith('.wmf'):
                    # If WMF and WebP exists, use WebP
                    webp_basename = basename.replace('.wmf', '.webp')
                    webp_path = os.path.join(image_dir, webp_basename)
                    if os.path.exists(webp_path):
                        block["src"] = webp_path
        for option in question["options"]:
            for block in option["blocks"]:
                if block["type"] == "image":
                    basename = os.path.basename(block["src"])
                    if basename in images_map:
                        block["src"] = os.path.join(image_dir, images_map[basename])
                    elif basename.endswith('.wmf'):
                        # If WMF and WebP exists, use WebP
                        webp_basename = basename.replace('.wmf', '.webp')
                        webp_path = os.path.join(image_dir, webp_basename)
                        if os.path.exists(webp_path):
                            block["src"] = webp_path

if __name__ == "__main__":
    docx_file = "test.docx"
    tex_output = "temp.tex"
    json_output = "output.json"

    # Step 1: extract and convert images
    images_map = extract_and_convert_images(docx_file, "media")

    # Step 2: convert DOCX -> LaTeX
    latex_content = convert_docx_to_latex(docx_file, tex_output)

    # Step 3: parse LaTeX to JSON
    questions = parse_latex_to_json(latex_content)

    # Step 4: update image srcs to WebP
    update_image_srcs(questions, images_map, "media")

    # Step 5: save JSON
    with open(json_output, "w", encoding="utf-8") as f:
        json.dump({"questions": questions}, f, ensure_ascii=False, indent=4)

    print("Extracted", len(questions), "questions")