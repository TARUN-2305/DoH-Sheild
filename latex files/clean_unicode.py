import re

def clean_file():
    with open(r'c:\Users\91636\.gemini\antigravity-ide\scratch\DoH-Sheild\doh_shield_paper_humanized.tex', 'r', encoding='utf-8') as f:
        content = f.read()

    # Log non-ASCII characters
    non_ascii = set()
    for char in content:
        if ord(char) > 127:
            non_ascii.add(char)
    print("Non-ASCII characters found:", [c for c in non_ascii])

    # Replacements dictionary
    replacements = {
        '∆': r'\Delta ',
        'ε': r'\varepsilon ',
        '≤': r'\le ',
        '≥': r'\ge ',
        '−': '-',  # Unicode minus to standard hyphen
        '˜': '~',  # Unicode tilde
        'κ': r'\kappa ',
        'δ': r'\delta ',
        '✓': r'\checkmark',
        '–': '--',  # en-dash
        '—': '---', # em-dash
        '“': '``',  # Left double quote
        '”': "''",  # Right double quote
        '‘': '`',   # Left single quote
        '’': "'",   # Right single quote
        'µ': r'\mu ',
        '·': r'\cdot ',
        '∞': r'\infty ',
        '⌊': r'\lfloor ',
        '⌋': r'\rfloor ',
        'ˆ': '^',
    }

    # Perform simple replacements
    for char, replacement in replacements.items():
        content = content.replace(char, replacement)

    # Clean up specific formula syntax that may have been humanized incorrectly
    # e.g., t˜j -> \tilde{t}_j
    content = content.replace(r't~j', r'\tilde{t}_j')
    content = content.replace(r't\tildej', r'\tilde{t}_j')
    content = content.replace(r't\tilde_j', r'\tilde{t}_j')
    content = content.replace(r't\tilde{~}_j', r'\tilde{t}_j')
    content = content.replace(r'Yj', r'Y_j')
    content = content.replace(r'tj', r't_j')
    content = content.replace(r'N^pkt', r'N_{\text{pkt}}')
    content = content.replace(r'N^ pkt', r'N_{\text{pkt}}')
    content = content.replace(r'\delta_\kappa mod 3', r'\delta_\kappa') # Wait, let's fix (3): c' = (c + \delta_\kappa) \bmod K
    
    # Check if there are remaining non-ASCII characters
    remaining = set()
    for char in content:
        if ord(char) > 127:
            remaining.add(char)
            
    if remaining:
        print("Warning: Remaining non-ASCII characters:", [c for c in remaining])
    else:
        print("All non-ASCII characters resolved successfully!")

    with open(r'c:\Users\91636\.gemini\antigravity-ide\scratch\DoH-Sheild\doh_shield_paper_humanized.tex', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    clean_file()
