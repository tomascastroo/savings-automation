from dataclasses import dataclass
from typing import List, Optional
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
from io import BytesIO

@dataclass
class OcrResult:
    text: str
    pages: int

class OcrEngine:
    async def extract_text(self, file_bytes: bytes) -> OcrResult:
        raise NotImplementedError

class TesseractOcrEngine(OcrEngine):
    async def extract_text(self, file_bytes: bytes) -> OcrResult:
        try:
            # Try PDF first
            images = convert_from_bytes(file_bytes)
            texts = [pytesseract.image_to_string(img) for img in images]
            return OcrResult(text="\n".join(texts), pages=len(images))
        except Exception:
            # Fallback: treat as image
            img = Image.open(BytesIO(file_bytes))
            txt = pytesseract.image_to_string(img)
            return OcrResult(text=txt, pages=1)
