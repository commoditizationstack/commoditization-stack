"""Tab Appendix B — phase-conditional CAPM/WACC with eleven equations."""
import streamlit as st
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FIG_DIR = PROJECT_ROOT / "outputs" / "figures"


def render(global_params: dict):
    st.header("Appendix B — Two-Phase Reformulation of Canonical Formulas")
    st.markdown(
        """
        Appendix B reformulates CAPM, WACC, EVA, ROI, and the Gordon perpetuity
        as **phase-conditional** under the post-AI double-valley dynamic of
        Section 6.5. Eleven numbered equations make the reformulation explicit;
        a numerical demonstration on NeuroCertify and DataFlow Pro shows that
        the classical EVA framework masks a Phase-2 destruction-of-value period
        of approximately 23 per cent for Layer-4-heavy firms.
        """
    )

    st.subheader("Eleven numbered equations")

    eq_files = [
        ("eq_B1_classical_capm_beta.png", "B.1", "Classical levered beta"),
        ("eq_B2_classical_ke.png", "B.2", "Classical cost of equity"),
        ("eq_B3_phase_beta.png", "B.3", "Phase-conditional levered beta"),
        ("eq_B4_phase_ke.png", "B.4", "Phase-conditional cost of equity"),
        ("eq_B5_classical_wacc.png", "B.5", "Classical WACC"),
        ("eq_B6_phase_wacc.png", "B.6", "Phase-conditional WACC"),
        ("eq_B7_phase_eva.png", "B.7", "Phase-conditional EVA"),
        ("eq_B8_phase_roi.png", "B.8", "Phase-conditional ROI test"),
        ("eq_B9_phase_perpetuity.png", "B.9", "Phase-conditional Gordon perpetuity"),
        ("eq_B10_compounded_pv.png", "B.10", "Compounded discount factor"),
        ("eq_B11_two_phase_dcf.png", "B.11", "Two-phase enterprise value (full DCF)"),
    ]

    for fname, num, label in eq_files:
        fp = FIG_DIR / fname
        col1, col2, col3 = st.columns([1, 4, 1])
        with col2:
            if fp.exists():
                st.image(str(fp), use_container_width=True)
                st.caption(f"({num}) — {label}")
            else:
                st.warning(f"Equation {num} image missing.")

    st.markdown("---")

    st.subheader("Numerical demonstration")
    fig_titles = [
        ("fig19_two_phase_cost_of_capital.png",
         "Cost-of-capital trajectory by phase",
         "Phase-conditional WACC and Ke trajectories for NeuroCertify (left) "
         "and DataFlow Pro (right). NeuroCertify's Phase-2 jump is 1.67 pp "
         "(Layer-6 protection); DataFlow Pro's is 3.01 pp (Layer-4 exposure). "
         "The 1.34-pp asymmetry is the operational realization in WACC space "
         "of the seven-layer framework's claim about defensibility migration."),
        ("fig20_two_phase_eva_trajectory.png",
         "EVA trajectory: classical vs two-phase",
         "Year-by-year EVA under classical single-WACC formulation (grey) "
         "versus two-phase phase-conditional WACC formulation (colored). "
         "The classical formulation understates DataFlow Pro's Phase-2 "
         "value destruction by approximately 23 per cent."),
    ]

    for fname, title, caption in fig_titles:
        fp = FIG_DIR / fname
        st.markdown(f"#### {title}")
        if fp.exists():
            st.image(str(fp), caption=caption, use_container_width=True)
        else:
            st.warning(f"Figure {fname} missing. Run scripts/run_appendix_b.py.")

    st.markdown("---")

    st.markdown(
        """
        ### Run with custom phase parameters
        ```bash
        python scripts/run_appendix_b.py
        ```
        Edit the `PhaseParameters` dataclass in `src/valuation_two_phase.py`
        to set custom beta jumps, D/E shifts, and Kd spreads for each phase.
        """
    )
