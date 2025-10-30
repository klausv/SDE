$$
\begin{aligned}
C(t) &= C_{\text{import}}(t) + C_{\text{effekt}}(\text{måned}(t)) - R_{\text{eksport}}(t) \\[4pt]
\textbf{Importkostnad:}\quad
C_{\text{import}}(t) &= P_{\text{import}}(t)\,\Big[\, p_{\text{spot}}(t) + p_{\text{energi}}(t) + p_{\text{elavgift}}(t) + p_{\text{påslag}} \,\Big]\,(1+\text{mva}) \\[8pt]
\textbf{Effekttariff (månedlig):}\quad
C_{\text{effekt}}(m) &= f\!\left(\max_{t \in \text{måned}(m)} P_{\text{import}}(t)\right) \\[4pt]
\text{der }\;
f(P_{\max}) &= 
\begin{cases}
136, & 0 \le P_{\max} < 2 \text{ kW} \\
232, & 2 \le P_{\max} < 5 \text{ kW} \\
372, & 5 \le P_{\max} < 10 \text{ kW} \\
\vdots \\
5600, & P_{\max} \ge 100 \text{ kW}
\end{cases} \\[8pt]
\textbf{Eksportinntekt:}\quad
R_{\text{eksport}}(t) &= P_{\text{eksport}}(t)\,\big( p_{\text{spot}}(t) - p_{\text{påslag}} \big)
\end{aligned}
$$