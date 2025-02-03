import pdfplumber
import re
import json
import cv2
import numpy as np
import os
from pdf2image import convert_from_path
from typing import Dict, List, Tuple, Set

def get_check_pages(pdf_path: str) -> Set[int]:
    """
    Find pages containing check images by looking for "IMAGES FOR" text.
    Returns set of actual page numbers.
    """
    check_pages = set()
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if "IMAGES FOR" in text:
                page_header_match = re.search(r'Page (\d+) of', text)
                if page_header_match:
                    actual_page = int(page_header_match.group(1))
                    check_pages.add(actual_page)

    return check_pages

def convert_pdf_to_images(pdf_path: str, output_dir: str, check_pages: Set[int]) -> Dict[int, str]:
    """
    Convert only the PDF pages containing check images.
    Returns: Dict[page_number, image_path]
    """
    os.makedirs(output_dir, exist_ok=True)
    page_images = {}
    
    # Convert only check pages

    for page_num in sorted(check_pages):
        # convert_from_path is 1-indexed
        images = convert_from_path(pdf_path, first_page=page_num+1, last_page=page_num+1)
        if images:
            image_path = os.path.join(output_dir, f'page_{page_num}.png')
            images[0].save(image_path, 'PNG')
            page_images[page_num] = image_path
    
    return page_images

def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF document using pdfplumber."""
    full_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text.append(text)
    return "\n".join(full_text)

def parse_checks(text):
    """Parses check transactions from extracted text."""
    transactions = []
    in_check_section = False
    
    # Pattern to also capture asterisk
    check_pattern = re.compile(
        r"(\d+\*?)\s+([A-Za-z]{3}\s+\d{1,2})\s+(\d+)\s+(\d{1,3}(?:,\d{3})*\.\d{2})"
    )

    for line in text.split('\n'):
        if "Checks Presented Conventionally" in line:
            in_check_section = True
            continue

        if in_check_section:
            if "Balance Summary" in line:
                break

            matches = check_pattern.findall(line)
            for match in matches:
                check_no = match[0]  
                date_str = match[1]
                ref_num = match[2]
                amount_str = match[3].replace(',', '')

                transactions.append({
                    "check_no": check_no,
                    "date": date_str,
                    "amount": float(amount_str),
                    "description": "",
                    "image_file": ""
                })

    return {"transactions": transactions}


def extract_check_numbers_from_pdf(pdf_path: str) -> Dict[int, List[str]]:
    """Extract check numbers from PDF text, organized by page."""
    check_numbers_by_page = {}
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if "IMAGES FOR" not in text:
                continue
            
            page_header_match = re.search(r'Page (\d+) of', text)
            if page_header_match:
                actual_page = int(page_header_match.group(1))
            else:
                continue
                
            lines = text.split('\n')
            start_idx = -1
            for i, line in enumerate(lines):
                if "Account Number 1-455-7029-8821" in line:
                    start_idx = i + 1
                    break
            
            if start_idx == -1:
                continue
                
            check_numbers = []
            for line in lines[start_idx:]:
                if not re.match(r'^\d{4}\*?\s+', line):
                    continue
                
                parts = line.split()
                if len(parts) >= 7:
                    left_check = parts[0]
                    for i, part in enumerate(parts[3:], 3):
                        if re.match(r'^\d{4}\*?$', part):
                            right_check = part
                            check_numbers.extend([left_check, right_check])
                            break
                elif len(parts) >= 3:
                    check_numbers.append(parts[0])
            
            if check_numbers:
                check_numbers_by_page[actual_page] = check_numbers
    
    return check_numbers_by_page

def detect_and_save_checks(image_path: str, output_dir: str, page_num: int, 
                          check_numbers: List[str]) -> List[str]:
    """
    Detect checks in image and save them. Returns list of saved file paths.
    """
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY_INV, 11, 2)
    kernel = np.ones((3,3), np.uint8)
    morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    min_check_width = 500
    min_check_height = 150
    min_aspect_ratio = 2.0
    max_aspect_ratio = 3.5
    padding = 15
    row_tolerance = 50
    
    valid_checks = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        aspect_ratio = float(w)/h
        
        if (w >= min_check_width and h >= min_check_height and 
            min_aspect_ratio <= aspect_ratio <= max_aspect_ratio):
            valid_checks.append({
                'y': y,
                'x': x,
                'coords': (max(0, x - padding),
                          max(0, y - padding),
                          min(img.shape[1], x + w + padding),
                          min(img.shape[0], y + h + padding * 2))
            })
    
    rows = {}
    for check in valid_checks:
        row_key = check['y'] // row_tolerance
        if row_key not in rows:
            rows[row_key] = []
        rows[row_key].append(check)
    
    sorted_checks = []
    for row_key in sorted(rows.keys()):
        sorted_checks.extend(sorted(rows[row_key], key=lambda x: x['x']))
    
    saved_paths = []
    os.makedirs(output_dir, exist_ok=True)
    
    for check, number in zip(sorted_checks, check_numbers):
        x_start, y_start, x_end, y_end = check['coords']
        check_image = img[y_start:y_end, x_start:x_end]
        
        output_path = os.path.join(output_dir, f"{page_num}_{number}.png")
        cv2.imwrite(output_path, check_image)
        saved_paths.append(output_path)
    
    return saved_paths

def process_document(pdf_path: str, output_dir: str) -> Dict:
    """
    Process PDF document and return integrated check information.
    """
    # Extract transaction data
    text = extract_text_from_pdf(pdf_path)
    result = parse_checks(text)
    
    # Find pages with checks
    check_pages = get_check_pages(pdf_path)
    
    # Convert only check pages to images
    image_dir = os.path.join(output_dir, "pages")
    page_images = convert_pdf_to_images(pdf_path, image_dir, check_pages)
    
    # Extract check numbers and images
    check_numbers_by_page = extract_check_numbers_from_pdf(pdf_path)
    
    # Lookup for check numbers to their image files
    check_to_image = {}
    for page_num, check_numbers in check_numbers_by_page.items():
        if page_num in page_images:
            image_paths = detect_and_save_checks(
                page_images[page_num], 
                os.path.join(output_dir, "checks"),
                page_num,
                check_numbers
            )
            for check_num, image_path in zip(check_numbers, image_paths):
                check_to_image[check_num] = image_path
    
    # Update transaction records with image files
    for transaction in result["transactions"]:
        check_no = transaction["check_no"]
        # Try exact match first
        if check_no in check_to_image:
            transaction["image_file"] = check_to_image[check_no]
        else:
            # Try matching without asterisk
            base_check_no = check_no.rstrip('*')
            asterisk_check_no = base_check_no + '*'
            if asterisk_check_no in check_to_image:
                transaction["image_file"] = check_to_image[asterisk_check_no]
            elif base_check_no in check_to_image:
                transaction["image_file"] = check_to_image[base_check_no]
    
    return result

