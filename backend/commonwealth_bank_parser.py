import pdfplumber
import re
from decimal import Decimal
from typing import List, Dict, Optional, Tuple


def parse_full_featured_statement(pdf_path: str) -> Dict:
    """
    A parser that:
      - Finds 'OPENING BALANCE' and 'CLOSING BALANCE' as boundaries.
      - Merges multi-line transactions if next line doesn't start with a new date.
      - Splits a merged line into multiple transactions if it contains multiple date patterns.
      - Parses multiple amounts from the Debit and Credit columns if needed,
        so each date-chunk in a line can get its *own* amount.
    """

    # Regex to detect date patterns like "14 Oct 2017" or "14 Oct"
    DATE_REGEX = re.compile(r"\b(\d{1,2}\s+[A-Za-z]{3}(?:\s+\d{4})?)\b", re.IGNORECASE)

    REQUIRED_HEADERS = {"Date", "Transaction", "Debit", "Credit"}

    LINE_TOLERANCE = 2.0
    COLUMN_BUFFER_DEBIT_CREDIT = 6.0
    COLUMN_BUFFER_TRANSACTION = 60.0

    statement_info = {"opening_balance": None, "closing_balance": None}
    transactions = []

    ################ HELPER FUNCTIONS ################
    def group_words_by_line(words: List[Dict], tolerance: float) -> List[List[Dict]]:
        """Group pdfplumber words into lines by approximate y-coordinate."""
        lines = []
        for w in words:
            y = w["top"]
            placed = False
            for line in lines:
                avg_y = sum(word["top"] for word in line) / len(line)
                if abs(y - avg_y) <= tolerance:
                    line.append(w)
                    placed = True
                    break
            if not placed:
                lines.append([w])
        for ln in lines:
            ln.sort(key=lambda x: x["x0"])
        lines.sort(key=lambda ln: ln[0]["top"])
        return lines

    def sanitize_amount_str(raw: str) -> Optional[Decimal]:
        """
        Attempt to parse a numeric string like "70.00", removing commas etc.
        Return None if invalid.
        """
        raw = raw.replace(",", "").replace("$", "").strip()
        if not raw:
            return None
        try:
            return Decimal(raw)
        except:
            return None

    def find_first_opening_balance(lines: List[List[Dict]]):
        for line in lines:
            text_line = " ".join(w["text"] for w in line).upper()
            if "OPENING" in text_line and "BALANCE" in text_line:
                m = re.search(r"OPENING\s+BALANCE\s+(\S+)", text_line)
                if m:
                    amt = sanitize_amount_str(m.group(1).replace("CR","").replace("DR",""))
                    if amt is not None:
                        statement_info["opening_balance"] = str(amt)
                return line[0]["top"]
        return None

    def find_last_closing_balance(lines: List[List[Dict]]):
        last_top = None
        for line in lines:
            text_line = " ".join(w["text"] for w in line).upper()
            if "CLOSING" in text_line and "BALANCE" in text_line:
                last_top = line[0]["top"]
                m = re.search(r"CLOSING\s+BALANCE\s+(\S+)", text_line)
                if m:
                    amt = sanitize_amount_str(m.group(1).replace("CR","").replace("DR",""))
                    if amt is not None:
                        statement_info["closing_balance"] = str(amt)
        return last_top

    def line_has_required_headers(line_words: List[Dict], headers: set) -> bool:
        txts = {w["text"].strip().lower() for w in line_words}
        return all(h.lower() in txts for h in headers)

    def find_header_columns(line_words: List[Dict]) -> Dict[str, Tuple[float,float]]:
        """On a line known to contain all required headers, build {header: (x0,x1)}."""
        col_map = {}
        for w in line_words:
            lw = w["text"].strip().lower()
            for hdr in REQUIRED_HEADERS:
                if lw == hdr.lower():
                    col_map[hdr] = (w["x0"], w["x1"])
        return col_map

    def find_columns_in_lines(lines: List[List[Dict]]) -> Dict[str, Tuple[float,float]]:
        for ln in lines:
            if line_has_required_headers(ln, REQUIRED_HEADERS):
                return find_header_columns(ln)
        return {}

    def in_column(x_mid: float, col: Tuple[float,float], buffer: float) -> bool:
        return (col[0] - buffer) <= x_mid <= (col[1] + buffer)

    def extract_date_chunks(text: str) -> List[Tuple[str,str]]:
        """
        Splits a line's text into multiple (date_string, description_string) chunks 
        if the line contains multiple date matches.
        For example:
          "01 Nov Direct Credit ... 01 Nov Transfer from ..." => 2 chunks
        find each date via DATE_REGEX, then everything until the next date is that chunk's description.
        Return a list of (date_str, desc_str).
        """
        matches = list(DATE_REGEX.finditer(text))
        if not matches:
            return []
        
        chunks = []
        for i in range(len(matches)):
            start_idx = matches[i].start()
            date_val = matches[i].group(1)
            # End of chunk is up to the next date (or end of text)
            end_idx = matches[i+1].start() if i+1 < len(matches) else len(text)
            desc_part = text[start_idx:end_idx]
            desc_str = desc_part[len(date_val):].strip()
            chunks.append((date_val, desc_str))
        
        return chunks

    def parse_all_amounts_in_line(line_words: List[Dict], columns: Dict[str, Tuple[float,float]]) -> List[Decimal]:
        """
        Return a list of amounts in the order they appear left-to-right.
        * Debit column amounts are negative
        * Credit column amounts are positive
        This way, if the line has multiple transactions, we can pick them up individually.
        """
        if not columns:
            return []

        amounts_with_x = []

        # Gather words from the Debit column
        if "Debit" in columns:
            d_col = columns["Debit"]
            for w in line_words:
                x_mid = (w["x0"] + w["x1"]) / 2
                if in_column(x_mid, d_col, COLUMN_BUFFER_DEBIT_CREDIT):
                    # find all numeric tokens
                    matches = re.findall(r"[0-9,\.]+", w["text"])
                    for m in matches:
                        val = sanitize_amount_str(m)
                        if val is not None:
                            # Mark it negative
                            amounts_with_x.append((x_mid, -val))

        # Gather words from the Credit column
        if "Credit" in columns:
            c_col = columns["Credit"]
            for w in line_words:
                x_mid = (w["x0"] + w["x1"]) / 2
                if in_column(x_mid, c_col, COLUMN_BUFFER_DEBIT_CREDIT):
                    matches = re.findall(r"[0-9,\.]+", w["text"])
                    for m in matches:
                        val = sanitize_amount_str(m)
                        if val is not None:
                            # Mark it positive
                            amounts_with_x.append((x_mid, val))

        # Sort by x-coordinate just in case they overlap or appear in different positions
        amounts_with_x.sort(key=lambda x: x[0])

        # Return them in left-to-right order
        return [amt for (_, amt) in amounts_with_x]

    ################ MAIN LOGIC ################
    all_pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, pg in enumerate(pdf.pages):
            words = pg.extract_words()
            lines = group_words_by_line(words, LINE_TOLERANCE)
            all_pages.append((page_idx, lines))

    # Find opening/closing boundaries
    opening_boundary = None  
    closing_boundary = None  

    for p_idx, lines in all_pages:
        ob = find_first_opening_balance(lines)
        if ob is not None and opening_boundary is None:
            opening_boundary = (p_idx, ob)
        cb = find_last_closing_balance(lines)
        if cb is not None:
            closing_boundary = (p_idx, cb)

    def is_in_range(page_idx: int, line_top: float) -> bool:
        """Return True if (page_idx,line_top) is after opening boundary and before closing boundary."""
        if not opening_boundary and not closing_boundary:
            return True
        if opening_boundary and not closing_boundary:
            (op_p, op_top) = opening_boundary
            if page_idx < op_p: return False
            if page_idx == op_p and line_top < op_top: return False
            return True
        if not opening_boundary and closing_boundary:
            (cl_p, cl_top) = closing_boundary
            if page_idx > cl_p: return False
            if page_idx == cl_p and line_top > cl_top: return False
            return True
        
        (start_p, start_top) = opening_boundary
        (end_p, end_top) = closing_boundary
        if page_idx < start_p: return False
        if page_idx == start_p and line_top < start_top: return False
        if page_idx > end_p: return False
        if page_idx == end_p and line_top > end_top: return False
        return True

    # Find columns (Date,Transaction,Debit,Credit) in any page
    columns = {}
    for p_idx, lines in all_pages:
        if not columns:
            c = find_columns_in_lines(lines)
            if len(c) >= len(REQUIRED_HEADERS):
                # unify the keys
                norm = {}
                for k, v in c.items():
                    K = k.capitalize()
                    if K in REQUIRED_HEADERS:
                        norm[K] = v
                if len(norm) == len(REQUIRED_HEADERS):
                    columns = norm

    if not columns:
        # Could not find the header row => can't parse amounts
        return {"statement_info": statement_info, "transactions": []}

    # Merge lines on each page, skipping lines that contain 'OPENING BALANCE'/'CLOSING BALANCE'
    for p_idx, lines in all_pages:
        lines_inrange = [ln for ln in lines if is_in_range(p_idx, ln[0]['top'])]

        merged_lines = []
        current_line_words = None

        def line_contains_open_or_close(ln_words: List[Dict]) -> bool:
            t = " ".join(w["text"] for w in ln_words).upper()
            return ("OPENING BALANCE" in t) or ("CLOSING BALANCE" in t)

        def line_starts_with_date(ln_words: List[Dict]) -> bool:
            joined = " ".join(w["text"] for w in ln_words).strip()
            # Check if there's a date at the start
            return bool(DATE_REGEX.match(joined))

        for ln in lines_inrange:
            if line_contains_open_or_close(ln):
                continue

            if line_starts_with_date(ln):
                if current_line_words:
                    merged_lines.append(current_line_words)
                current_line_words = ln
            else:
                if current_line_words is None:
                    current_line_words = ln
                else:
                    current_line_words = current_line_words + ln

        if current_line_words:
            merged_lines.append(current_line_words)

        # Parse each merged line
        for mline in merged_lines:
            line_text = " ".join(w["text"] for w in mline)

            # Extract *all* amounts from the line (in left->right order)
            amounts = parse_all_amounts_in_line(mline, columns)
            if not amounts:
                continue  # skip if no amounts

            # Identify date-chunks from the entire line_text or from Transaction column only
            desc_col_text = " ".join(w["text"] for w in mline if in_column(
                (w["x0"]+w["x1"])/2, columns["Transaction"], COLUMN_BUFFER_TRANSACTION
            ))
            # Try to find multiple date chunks in that transaction text
            date_chunks = extract_date_chunks(desc_col_text)
            if not date_chunks:
                # fallback to entire line_text
                date_chunks = extract_date_chunks(line_text)
            if not date_chunks:
                # if still none, skip
                continue

            pairs_to_create = min(len(date_chunks), len(amounts))

            for i in range(pairs_to_create):
                d_val, d_desc = date_chunks[i]
                amt_val = amounts[i]

                # Clean up
                d_val = d_val.strip()
                d_desc = d_desc.strip()
                if not d_val:
                    continue
                # skip if it says opening/closing
                if "OPENING BALANCE" in d_desc.upper() or "CLOSING BALANCE" in d_desc.upper():
                    continue

                txn = {
                    "date": d_val,
                    "description": d_desc,
                    "amount": float(amt_val)
                }
                transactions.append(txn)
            
    return {
        "statement_info": statement_info,
        "transactions": transactions
    }