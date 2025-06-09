import re
import random

def parse_lots(lines):
    sample_lines = random.sample(lines, min(10, len(lines)))
    print("Sample results:")
    for line in sample_lines: 
        vintage = extract_vintage(line)
        print(line)
        print(vintage)
        print()

def extract_vintage(line: str) -> str:
    pattern1 = r'(?:^|\|)\s*(\d{4})(?=\s+[A-Za-z])'
    years1 = re.findall(pattern1, line, re.MULTILINE)
    
    
    pattern2 = r'(\d{4})\s+(?=[A-Z][a-zA-Z])'
    years2 = re.findall(pattern2, line)
    
    all_years = years1 + years2
    
    valid_years = [year for year in all_years if 1800 <= int(year) <= 2030]
    
    return list(valid_years)

with open("lots.txt", "r", encoding='utf-8') as f:
    content = f.read()
    lines = content.splitlines()

parse_lots(lines)
