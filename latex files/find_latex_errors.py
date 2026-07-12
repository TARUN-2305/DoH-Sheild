import re

def verify_latex_integrity():
    with open(r'c:\Users\91636\.gemini\antigravity-ide\scratch\DoH-Sheild\doh_shield_paper_humanized.tex', 'r', encoding='utf-8') as f:
        content = f.read()

    errors = []

    # 1. Check for duplicate labels
    labels = re.findall(r'\\label\{(.*?)\}', content)
    duplicate_labels = set([x for x in labels if labels.count(x) > 1])
    if duplicate_labels:
        errors.append(f"Duplicate labels found: {duplicate_labels}")

    # 2. Check for unresolved references
    refs = re.findall(r'\\ref\{(.*?)\}', content)
    label_set = set(labels)
    unresolved_refs = [r for r in refs if r not in label_set]
    if unresolved_refs:
        errors.append(f"Unresolved references (ref without matching label): {set(unresolved_refs)}")

    # 3. Check for unresolved citations
    cites = []
    # Find all cite arguments e.g., \cite{cira2020, sirinam2018}
    for match in re.finditer(r'\\cite\{(.*?)\}', content):
        items = [x.strip() for x in match.group(1).split(',')]
        cites.extend(items)
        
    bibitems = re.findall(r'\\bibitem\{(.*?)\}', content)
    bibitem_set = set(bibitems)
    unresolved_cites = [c for c in cites if c not in bibitem_set]
    if unresolved_cites:
        # In IEEE papers, sometimes citations are numbers like [1], [3]. If they wrote \cite{1}, check it.
        # But if they wrote standard bibitem labels, they must match.
        errors.append(f"Unresolved citations (cite without bibitem): {set(unresolved_cites)}")

    # 4. Check for \newtheorem in document body
    document_start = content.find('\\begin{document}')
    newtheorem_idx = content.find('\\newtheorem')
    if newtheorem_idx != -1 and newtheorem_idx > document_start:
        errors.append("Error: \\newtheorem definition is in the document body. It must be moved to the preamble.")

    print(f"LaTeX integrity check results: {len(errors)} issues found.")
    for err in errors:
        print(" - " + err)

if __name__ == '__main__':
    verify_latex_integrity()
