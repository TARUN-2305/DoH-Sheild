import re
import difflib

def clean_text(text):
    # Remove latex commands first, then arguments
    text = re.sub(r'\\(?:begin|end|section|subsection|subsubsection|author|title|and|maketitle|IEEEauthorblockN|IEEEauthorblockA|bibliographystyle|bibliography)\b', '', text)
    # Remove simple commands like \textbf{...} but keep the content inside the braces!
    # For example, \textbf{hello} -> hello
    text = re.sub(r'\\[a-zA-Z*]+(?:\[.*?\])?(?=\{)', '', text)
    # Remove braces
    text = text.replace('{', '').replace('}', '').replace('\\', '')
    # Remove inline math $...$
    text = re.sub(r'\$.*?\$', '', text)
    # Remove math equations \[...\] or $$...$$
    text = re.sub(r'\\\[.*?\\\]', '', text, flags=re.DOTALL)
    text = re.sub(r'\$\$.*?\$\$', '', text, flags=re.DOTALL)
    # Remove latex comments
    text = re.sub(r'%.*?\n', '\n', text)
    # Normalize whitespaces
    text = ' '.join(text.split())
    # Lowercase
    text = text.lower()
    # Remove punctuation
    text = re.sub(r'[^\w\s]', '', text)
    return text

def verify():
    with open(r'c:\Users\91636\Downloads\In this work, we present the protec.txt', 'r', encoding='utf-8') as f:
        source = f.read()
    
    with open(r'c:\Users\91636\.gemini\antigravity-ide\scratch\DoH-Sheild\doh_shield_paper_humanized.tex', 'r', encoding='utf-8') as f:
        latex = f.read()
        
    cleaned_source = clean_text(source)
    cleaned_latex = clean_text(latex)
    
    # Split into paragraphs in source
    source_paragraphs = [p.strip() for p in source.split('\n\n') if p.strip()]
    
    found_count = 0
    missing = []
    
    for i, p in enumerate(source_paragraphs):
        cleaned_p = clean_text(p)
        if not cleaned_p or len(cleaned_p) < 10:
            continue
        
        # Check if a substantial part of cleaned_p is in cleaned_latex
        # Let's check with difflib
        seq = difflib.SequenceMatcher(None, cleaned_p, cleaned_latex)
        match = seq.find_longest_match(0, len(cleaned_p), 0, len(cleaned_latex))
        
        match_ratio = match.size / len(cleaned_p) if len(cleaned_p) > 0 else 0
        
        # We can also check if a subset of words matches
        p_words = set(cleaned_p.split())
        latex_words = set(cleaned_latex.split())
        common_words = p_words.intersection(latex_words)
        word_overlap = len(common_words) / len(p_words) if p_words else 0
        
        # If either sequence matcher matches a good chunk, or word overlap is high
        if match_ratio > 0.4 or word_overlap > 0.7:
            found_count += 1
        else:
            missing.append((i, p, match_ratio, word_overlap))
            
    print(f"Matched paragraphs from the new file: {found_count}/{len(source_paragraphs)}")
    if missing:
        print("\nParagraphs with low match:")
        for idx, p, ratio, word_ratio in missing[:5]:
            print(f"Paragraph {idx} (Seq match: {ratio:.2f}, Word overlap: {word_ratio:.2f}):")
            print(p[:200] + "...")
            print("-" * 50)
            
if __name__ == '__main__':
    verify()
