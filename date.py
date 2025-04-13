import re
from datetime import datetime

def extract_year_from_filename(filename):
    patterns = [
        r"(\d{4})(\d{2})(\d{2})",                         # e.g., 20250405
        r"[A-Za-z]+_(\w+)_\d{2}_(\d{4})",                 # Apr_09_2025
        r"(\d{4})-(\d{2})-(\d{2})",                       # 2025-04-06
        r"(\w+)\s+(\d{4})",                               # January 2025
        r"Statement-(\d{8})",                             # 20250323
    ]

    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            try:
                if len(match.groups()) == 3:
                    year, month, day = match.groups()
                    return int(year)
                elif len(match.groups()) == 2:
                    month_str, year = match.groups()
                    try:
                        return datetime.strptime(f"{month_str} {year}", "%B %Y").year
                    except:
                        return datetime.strptime(f"{month_str} {year}", "%b %Y").year
                elif len(match.groups()) == 1:
                    return int(match.group(1)[:4])
            except Exception:
                continue
    return 2024  # Default fallback

def format_date(date_str, filename):
    try:
        if re.match(r"\d{2}/\d{2}/\d{4}", date_str):
            return datetime.strptime(date_str, "%m/%d/%Y").strftime("%Y-%m-%d")
        elif re.match(r"\d{2}/\d{2}/\d{2}", date_str):
            return datetime.strptime(date_str, "%m/%d/%y").strftime("%Y-%m-%d")
        elif re.match(r"\d{2}/\d{2}", date_str):
            year = extract_year_from_filename(filename)
            return datetime.strptime(f"{date_str}/{year}", "%m/%d/%Y").strftime("%Y-%m-%d")
    except:
        return date_str
