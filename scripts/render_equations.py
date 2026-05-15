"""Generate publication-quality equation images for Appendix B of the paper.

Each equation is rendered as a transparent PNG via matplotlib mathtext,
sized to look like display-math in scientific papers.
The equation number is added to the right margin, separately, by the
docx-build step (the PNG itself contains only the equation).
"""
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib

# Use serif font matching scientific-paper convention
matplotlib.rcParams['mathtext.fontset'] = 'cm'      # Computer Modern (LaTeX-like)
matplotlib.rcParams['mathtext.default'] = 'regular'

OUT = Path("/home/claude/workspace/commoditization-stack-simulation/outputs/figures")
OUT.mkdir(parents=True, exist_ok=True)


def render_equation(latex: str, filename: str, fontsize: int = 18, padding: float = 0.06) -> None:
    """Render a LaTeX-style math expression as a transparent PNG."""
    fig = plt.figure(figsize=(8, 1.2))
    ax = fig.add_subplot(111)
    ax.axis('off')
    ax.text(0.5, 0.5, f"${latex}$",
            fontsize=fontsize, ha='center', va='center',
            transform=ax.transAxes)
    out = OUT / filename
    plt.savefig(out, dpi=200, bbox_inches='tight',
                pad_inches=padding, transparent=True)
    plt.close()
    print(f"  {filename}")


# ============================================================
# Appendix B equations
# ============================================================
print("Rendering Appendix B equations:")

# (B.1) Classical adjusted-CAPM (relevered beta)
render_equation(
    r"\beta_L \;=\; \beta_U \cdot \left[1 + (1 - \tau)\, \frac{D}{E}\right]",
    "eq_B1_classical_capm_beta.png"
)

# (B.2) Classical CAPM cost of equity
render_equation(
    r"K_e \;=\; R_f + \beta_L \cdot \mathrm{ERP}",
    "eq_B2_classical_ke.png"
)

# (B.3) Phase-conditional levered beta
render_equation(
    r"\beta_L(t) \;=\; \beta_U(\phi(t)) \cdot \left[1 + (1 - \tau)\, \frac{D}{E}(\phi(t))\right]",
    "eq_B3_phase_beta.png"
)

# (B.4) Phase-conditional cost of equity
render_equation(
    r"K_e(t) \;=\; R_f + \beta_L(t) \cdot \mathrm{ERP}",
    "eq_B4_phase_ke.png"
)

# (B.5) Classical WACC
render_equation(
    r"\mathrm{WACC} \;=\; \frac{E}{V}\, K_e \;+\; \frac{D}{V}\, K_d\, (1 - \tau)",
    "eq_B5_classical_wacc.png"
)

# (B.6) Phase-conditional WACC
render_equation(
    r"\mathrm{WACC}(t) \;=\; \left(\frac{E}{V}\right)\!(t)\, K_e(t) \;+\; \left(\frac{D}{V}\right)\!(t)\, K_d(t)\, (1 - \tau)",
    "eq_B6_phase_wacc.png", fontsize=17
)

# (B.7) Phase-conditional EVA
render_equation(
    r"\mathrm{EVA}(t) \;=\; \mathrm{NOPAT}(t) \;-\; \mathrm{WACC}(t) \cdot \mathrm{IC}(t)",
    "eq_B7_phase_eva.png"
)

# (B.8) Phase-conditional ROI test
render_equation(
    r"\mathrm{ROI}(t) \;=\; \frac{\mathrm{NOPAT}(t)}{\mathrm{IC}(t)} \;\;\;>\;\;\; \mathrm{WACC}(t) \;\;\Longleftrightarrow\;\; \text{firm creates value at } t",
    "eq_B8_phase_roi.png", fontsize=15
)

# (B.9) Phase-conditional Gordon perpetuity with second-valley drag
render_equation(
    r"\mathrm{TV} \;=\; \frac{\mathrm{FCF}_T \cdot (1 + g)}{\mathrm{WACC}_3 - g} \cdot (1 - \delta_{2V})",
    "eq_B9_phase_perpetuity.png"
)

# (B.10) Compounded discount factor for time-varying rates
render_equation(
    r"\mathrm{PV}(\mathrm{FCF}_t) \;=\; \frac{\mathrm{FCF}_t}{\prod_{s=1}^{t} (1 + r_s)}",
    "eq_B10_compounded_pv.png", fontsize=18
)

# (B.11) Two-phase enterprise value (full DCF expression)
render_equation(
    r"V_0 \;=\; \sum_{t=1}^{T} \frac{\mathrm{FCF}_t}{\prod_{s=1}^{t} (1 + \mathrm{WACC}(s))} \;+\; \frac{\mathrm{TV}}{\prod_{s=1}^{T} (1 + \mathrm{WACC}(s))}",
    "eq_B11_two_phase_dcf.png", fontsize=15
)

# ============================================================
# Appendix C equations (referenced in operational manual)
# ============================================================
print("\nRendering Appendix C equations:")

# (C.1) Layered firm-specific risk premium decomposition
render_equation(
    r"\pi_{\mathrm{firm}} \;=\; \sum_{i=1}^{7} \alpha_i \cdot w_i \cdot \mu_i",
    "eq_C1_layer_premium_decomposition.png"
)

# (C.2) TRL-modulated discount rate
render_equation(
    r"r(t) \;=\; r_{\mathrm{base}} + \pi_{\mathrm{TRL}}(\mathrm{TRL}(t)) + \pi_{\mathrm{firm}}",
    "eq_C2_trl_modulated_rate.png"
)

print("\nDone.")
