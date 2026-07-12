import re

def verify_latex(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Check matching environments
    begins = re.findall(r'\\begin\{([a-zA-Z*]+)\}', content)
    ends = re.findall(r'\\end\{([a-zA-Z*]+)\}', content)
    
    print(f"Total \\begin elements: {len(begins)}")
    print(f"Total \\end elements: {len(ends)}")
    
    if len(begins) != len(ends):
        print("Error: Number of \\begin and \\end blocks do not match!")
    
    # Track open environments stack
    stack = []
    lines = content.split('\n')
    for line_num, line in enumerate(lines, 1):
        for match in re.finditer(r'\\(begin|end)\{([a-zA-Z*]+)\}', line):
            cmd = match.group(1)
            env = match.group(2)
            if cmd == 'begin':
                stack.append((env, line_num))
            else:
                if not stack:
                    print(f"Error: \\end{{{env}}} on line {line_num} has no matching \\begin")
                else:
                    last_env, last_line = stack.pop()
                    if last_env != env:
                        print(f"Error: Mismatched environment. Found \\begin{{{last_env}}} on line {last_line} but closed with \\end{{{env}}} on line {line_num}")

    while stack:
        env, line_num = stack.pop()
        print(f"Error: Unclosed environment \\begin{{{env}}} on line {line_num}")
        
    # 2. Check brace balancing
    brace_count = 0
    for pos, char in enumerate(content):
        if char == '{':
            # Check if escaped
            if pos > 0 and content[pos-1] == '\\':
                continue
            brace_count += 1
        elif char == '}':
            if pos > 0 and content[pos-1] == '\\':
                continue
            brace_count -= 1
            if brace_count < 0:
                print(f"Warning: Excess closing brace '}}' around position {pos} (approx character context: {content[max(0, pos-20):pos+20]})")
                brace_count = 0
                
    if brace_count > 0:
        print(f"Warning: {brace_count} unclosed opening braces '{{'")
        
    # 3. Check for raw %, &, _, #, ^, etc. (often cause LaTeX compilation failure if not escaped)
    # Simple regex to look for unescaped characters outside of equations/environments
    for line_num, line in enumerate(lines, 1):
        # Remove comments from check
        comment_start = line.find('%')
        if comment_start != -1:
            # Check if % is escaped
            if comment_start > 0 and line[comment_start-1] == '\\':
                pass
            else:
                line = line[:comment_start] # ignore comments
        
        # Look for raw & (not part of table column separators or escaped)
        # Note: & is used in tables (tabular environment), so we skip lines containing tabular or block math if they use align/tabular
        # Look for raw _ (underscore) outside equations
        if '_' in line and not line.startswith('\\') and not '$' in line and not 'algorithm' in line and not '\\label' in line and not '\\includegraphics' in line and not '\\url' in line:
            # Check if it has escaped underscore
            raw_underscores = [m.start() for m in re.finditer(r'(?<!\\)_', line)]
            if raw_underscores:
                print(f"Warning: Unescaped underscore '_' on line {line_num}: {line.strip()}")

verify_latex(r'c:\Users\91636\.gemini\antigravity-ide\scratch\DoH-Sheild\doh_shield_paper_humanized.tex')
