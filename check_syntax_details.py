import re

def check_syntax():
    with open(r'c:\Users\91636\.gemini\antigravity-ide\scratch\DoH-Sheild\doh_shield_paper_humanized.tex', 'r', encoding='utf-8') as f:
        content = f.read()
        
    lines = content.split('\n')
    errors = []
    
    # 1. Find all tabular and equation/align blocks to ignore their internal & characters
    in_tabular_or_align = False
    
    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        if '\\begin{tabular}' in stripped or '\\begin{align}' in stripped or '\\begin{equation}' in stripped:
            in_tabular_or_align = True
        elif '\\end{tabular}' in stripped or '\\end{align}' in stripped or '\\end{equation}' in stripped:
            in_tabular_or_align = False
            continue
            
        # Get active text before comment
        comment_idx = -1
        for i, char in enumerate(line):
            if char == '%' and (i == 0 or line[i-1] != '\\'):
                comment_idx = i
                break
        check_line = line[:comment_idx] if comment_idx != -1 else line
        
        # Check raw & outside tables
        if not in_tabular_or_align:
            raw_ampersands = [m.start() for m in re.finditer(r'(?<!\\)&', check_line)]
            if raw_ampersands:
                errors.append(f"Line {line_num}: Unescaped '&' in text -> {line.strip()}")
                
        # Check raw % adjacent to numbers
        if comment_idx != -1:
            pre_char = line[comment_idx-1] if comment_idx > 0 else ''
            if pre_char.isdigit():
                errors.append(f"Line {line_num}: Unescaped '%' -> {line.strip()}")
                
        # Check raw _ outside math and safe commands
        in_math = False
        pos = 0
        while pos < len(check_line):
            char = check_line[pos]
            if char == '$':
                in_math = not in_math
            elif char == '_' and not in_math:
                if pos > 0 and check_line[pos-1] == '\\':
                    pass
                else:
                    # Check safe commands
                    is_safe = False
                    for safe in ['\\label', '\\ref', '\\cite', '\\includegraphics', '\\url', '\\texttt', '\\hyphenation', 'doh_shield', 'morph_engine', 'dummy_injector', 'feature_extractor']:
                        if safe in check_line:
                            is_safe = True
                            break
                    if not is_safe:
                        errors.append(f"Line {line_num}: Unescaped '_' -> {check_line[max(0, pos-15):pos+15].strip()}")
            pos += 1

    print(f"Total REAL syntax issues found: {len(errors)}")
    for err in errors:
        print(err)

if __name__ == '__main__':
    check_syntax()
