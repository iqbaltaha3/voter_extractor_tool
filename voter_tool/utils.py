import signal
import re
import numpy as np
import cv2
import pytesseract

# Global interrupt flag
INTERRUPTED = False

def signal_handler(sig, frame):
    global INTERRUPTED
    print("\n⚠️  Interrupt received, stopping gracefully...")
    INTERRUPTED = True

def setup_signal_handler():
    """Register the interrupt handler."""
    signal.signal(signal.SIGINT, signal_handler)

def extract_booth_name_from_images(images, pdf_stem):
    """
    Extract booth name from the first page of images.
    Falls back to PDF stem if not found.
    """
    for pil_img in images[:1]:
        img = np.array(pil_img)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)
        thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        raw = pytesseract.image_to_string(thresh, lang='hin+eng', config='--oem 3 --psm 3')
        lines = [l.strip() for l in raw.split('\n') if l.strip()]

        for i, line in enumerate(lines):
            if re.search(r'मतदान\s*स्थल\s*की\s*संख्या\s*और\s*नाम', line):
                for j in range(i + 1, min(i + 6, len(lines))):
                    candidate = lines[j]
                    if not re.match(r'^[\d|1I]+\s*[-–]', candidate):
                        continue
                    name = re.sub(r'^[\d|1I]+\s*[-–]\s*', '', candidate)
                    name = re.split(r'\s*-\s*इस\s*भाग\s*में', name)[0]
                    name = re.sub(r'\s+[A-Za-z]-\s.*$', '', name)
                    name = name.strip()
                    if name and re.search(r'[\u0900-\u097F]', name) and len(name) > 3:
                        return name

    part_match = re.search(r'HIN-(\d+)-WI', pdf_stem, re.IGNORECASE)
    if part_match:
        return f"Part_{part_match.group(1)}"
    return pdf_stem[:60]

def booth_to_filename(name: str) -> str:
    """Convert a booth name to a safe filename."""
    name = name.strip().lstrip('-').strip()
    name = re.sub(r'[\\/:*?"<>|@]', '', name)
    name = re.sub(r'[\(\)\s]+', '_', name)
    name = re.sub(r'_+', '_', name).strip('_')
    name = name[:100]
    return name + ".csv"

def preprocess_lines(raw_text: str) -> list:
    """Split lines, handling multiple 'नाम:' on the same line."""
    cleaned = []
    for line in raw_text.split('\n'):
        line = line.strip()
        if not line:
            continue
        naam_count = len(re.findall(r'नाम\s*:', line))
        if naam_count > 1:
            split_lines = re.split(r'(?<!\A)\s*(?=नाम\s*:)', line)
            cleaned.extend([s.strip() for s in split_lines if s.strip()])
        else:
            cleaned.append(line)
    return cleaned