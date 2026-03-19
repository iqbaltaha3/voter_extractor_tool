import cv2
import numpy as np
import pytesseract
import re

class OCREngine:
    """Perform OCR on an image and return cleaned text."""
    def __init__(self, lang: str = 'hin+eng'):
        self.lang = lang

    def extract_text(self, pil_image):
        # Convert PIL to OpenCV format
        img = np.array(pil_image)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)
        thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

        raw = pytesseract.image_to_string(thresh, lang=self.lang, config='--oem 3 --psm 3')
        # Apply common corrections
        text = re.sub(r'(लिग|fem|fam|om|art|Hee|ferts|feeT|oa|ar|हट|हल|m4)', 'लिंग', raw)
        text = re.sub(r'मकान सख्या', 'मकान संख्या', text)
        return text