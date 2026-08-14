import os
import pdfplumber
import docx

def extract_text_from_file(file_path: str) -> str:
    """Extracts raw text from a PDF or DOCX file."""
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    
    if ext == ".pdf":
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            print(f"Error parsing PDF {file_path}: {e}")
            
    elif ext in [".docx", ".doc"]:
        try:
            doc = docx.Document(file_path)
            for para in doc.paragraphs:
                text += para.text + "\n"
        except Exception as e:
            print(f"Error parsing DOCX {file_path}: {e}")
            
    else:
        # Fallback for plain text
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception:
            pass
            
    return text.strip()
