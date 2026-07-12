def fix_tables():
    with open(r'c:\Users\91636\.gemini\antigravity-ide\scratch\DoH-Sheild\doh_shield_paper_humanized.tex', 'r', encoding='utf-8') as f:
        content = f.read()

    # Table I Replacement
    old_table_i = r"""\begin{tabular}{lcccc}
\toprule
\textbf{Defense} & \textbf{Attack $F_1$} & \textbf{BW OH} & \textbf{Formal} & \textbf{Client-only} \
\midrule
None (baseline) & 0.9999 & 0\% & --- & --- \
RFC 8467 Padding [2] & $\sim$0.950 & $\sim$5\% & No & Yes \
Panchenko et al. [5] & $\sim$0.090 & $\sim$80\% & No & Yes \
Adaptive Tamaraw [12] & $\sim$0.080 & $\sim$200\% & Yes & Yes \
\textbf{DoH-Shield (ours)} & \textbf{0.1044} & \textbf{$<$40\%} & \textbf{Yes} & \textbf{Yes} \
\bottomrule
\end{tabular}"""

    new_table_i = r"""\begin{tabular}{lcccc}
\toprule
\textbf{Defense} & \textbf{Attack $F_1$} & \textbf{BW OH} & \textbf{Formal} & \textbf{Client-only} \\
\midrule
None (baseline) & 0.9999 & 0\% & --- & --- \\
RFC 8467 Padding [2] & $\sim$0.950 & $\sim$5\% & No & Yes \\
Panchenko et al. [5] & $\sim$0.090 & $\sim$80\% & No & Yes \\
Adaptive Tamaraw [12] & $\sim$0.080 & $\sim$200\% & Yes & Yes \\
\textbf{DoH-Shield (ours)} & \textbf{0.1044} & \textbf{$<$40\%} & \textbf{Yes} & \textbf{Yes} \\
\bottomrule
\end{tabular}"""

    # Table II Replacement
    old_table_ii = r"""\begin{tabular}{lc}
\toprule
\textbf{Metric} & \textbf{Value} \
\midrule
Total clusters ($K$) & 30 \
Pure clusters pre-merge & 9 \
Pure clusters post-merge & 0 \
Minimum cluster size ($k_{\min}$) & 343 \
Maximum cluster size & 66,519 \
Mean cluster size & 8,955 \
All clusters $l$-diversity $\ge 2$ & \checkmark \
\bottomrule
\end{tabular}"""

    new_table_ii = r"""\begin{tabular}{lc}
\toprule
\textbf{Metric} & \textbf{Value} \\
\midrule
Total clusters ($K$) & 30 \\
Pure clusters pre-merge & 9 \\
Pure clusters post-merge & 0 \\
Minimum cluster size ($k_{\min}$) & 343 \\
Maximum cluster size & 66,519 \\
Mean cluster size & 8,955 \\
All clusters $l$-diversity $\ge 2$ & \checkmark \\
\bottomrule
\end{tabular}"""

    # Table IV Replacement
    old_table_iv = r"""\begin{tabular}{cc}
\toprule
\textbf{Privacy Budget ($\varepsilon$)} & \textbf{Upper Bound $P_{\text{attack}}$} \
\midrule
$\varepsilon = 0.5$ & 60.94\% \
$\varepsilon = 1.0$ & 37.08\% \
$\varepsilon = 2.0$ & 13.82\% \
\bottomrule
\end{tabular}"""

    new_table_iv = r"""\begin{tabular}{cc}
\toprule
\textbf{Privacy Budget ($\varepsilon$)} & \textbf{Upper Bound $P_{\text{attack}}$} \\
\midrule
$\varepsilon = 0.5$ & 60.94\% \\
$\varepsilon = 1.0$ & 37.08\% \\
$\varepsilon = 2.0$ & 13.82\% \\
\bottomrule
\end{tabular}"""

    # Replace in content
    content = content.replace(old_table_i, new_table_i)
    content = content.replace(old_table_ii, new_table_ii)
    content = content.replace(old_table_iv, new_table_iv)

    with open(r'c:\Users\91636\.gemini\antigravity-ide\scratch\DoH-Sheild\doh_shield_paper_humanized.tex', 'w', encoding='utf-8') as f:
        f.write(content)

    print("Tables row separators fixed!")

if __name__ == '__main__':
    fix_tables()
