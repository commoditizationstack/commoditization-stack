"""Tab Layers — visualization of K7 effect on Layers 4 and 5.

All numeric knobs (modulation factor, collapse-threshold band, plot grid)
come from config/parameters.yaml.
"""
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from src import config

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FIG_DIR = PROJECT_ROOT / "outputs" / "figures"


def render(global_params: dict):
    st.header("The Seven-Layer Framework")
    st.markdown(
        """
        The seven-layer framework decomposes the knowledge-production stack
        into seven distinct layers, each with its own commoditization velocity
        and defensibility profile. Layer 7 — the cross-border knowledge regime —
        modulates the velocities of Layers 3, 4, and 5 in response to the
        trajectory of scientific decoupling and data-sovereignty fragmentation.
        """
    )

    tab_cfg = config.streamlit_ui()["tab_layers"]
    modulation = float(tab_cfg["effective_substitutability_modulation"])
    threshold_lo = float(tab_cfg["collapse_threshold_low"])
    threshold_hi = float(tab_cfg["collapse_threshold_high"])
    threshold_label = float(tab_cfg["collapse_threshold_label"])

    st.subheader("Live K₇ Sensitivity")
    K7 = global_params["K7"]

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Effective Layer-4 substitutability vs K₇**")
        fig, ax = plt.subplots(figsize=(6, 4))
        k7_grid = np.linspace(0, 1, 100)
        effective_substitutability = modulation * k7_grid
        ax.plot(k7_grid, effective_substitutability, color="#2C5282", linewidth=2.5)
        ax.scatter([K7], [modulation * K7], color="#C44536", s=120, zorder=5,
                   label=f"Current K₇={K7:.2f}")
        ax.axvspan(threshold_lo, threshold_hi, color="red", alpha=0.10,
                   label="Collapse threshold")
        ax.set_xlabel("K₇")
        ax.set_ylabel("Effective Layer-4 substitutability")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 0.8)
        ax.grid(True, linestyle=":", alpha=0.5)
        ax.legend(loc="upper left", fontsize=9)
        st.pyplot(fig)
        plt.close()

    with col2:
        st.markdown("**Layer-5 relative judgment value vs K₇**")
        fig, ax = plt.subplots(figsize=(6, 4))
        k7_grid_pos = np.linspace(0.05, 1, 100)
        judgment_value = 1.0 / k7_grid_pos
        ax.plot(k7_grid_pos, judgment_value, color="#E07B39", linewidth=2.5)
        if K7 > 0.05:
            ax.scatter([K7], [1.0 / K7], color="#C44536", s=120, zorder=5,
                       label=f"Current K₇={K7:.2f}")
        ax.axvspan(threshold_lo, threshold_hi, color="red", alpha=0.10)
        ax.set_xlabel("K₇")
        ax.set_ylabel("Layer-5 judgment value (relative, 1.0 at K₇=1.0)")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 8)
        ax.grid(True, linestyle=":", alpha=0.5)
        ax.legend(loc="upper right", fontsize=9)
        st.pyplot(fig)
        plt.close()

    st.markdown(
        f"""
        ### Interpretation
        - When K₇ is high (integrated regime), Layer-4 substitutability is high
          and the relative value of Layer 5 (judgment) is low.
        - When K₇ falls below the **collapse threshold** (≈ {threshold_label:.2f}),
          AI tooling loses cross-bloc capability, Layer-4 substitutability drops,
          and the relative value of Layer 5 rises sharply (more human curatorial
          judgment is needed to detect bloc-specific bias in fragmented frontier
          models).
        """
    )

    st.markdown("---")

    # ---- Paper parameters (read-only) ----
    with st.expander("📖 Paper parameters (read-only — edit config/parameters.yaml)"):
        st.markdown(
            "**Stack-layer velocities and substitutabilities (2026 baseline)** — "
            "source: `config/parameters.yaml` § stack_layers"
        )
        layers = config.load_parameters()["stack_layers"]
        rows = [
            {
                "layer": lid,
                "name": cfg.get("name", ""),
                "velocity": cfg.get("velocity"),
                "substitutability_2026": cfg.get("substitutability_2026"),
            }
            for lid, cfg in layers.items()
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)
        st.markdown(
            "**Knowledge regimes (Layer 7 defaults)** — "
            "source: `config/parameters.yaml` § knowledge_regimes.regimes"
        )
        regimes = config.knowledge_regime_defaults()
        reg_rows = [
            {
                "regime": slug,
                "K_coefficient": r["K_coefficient"],
                "bloc": r["bloc_assignment"],
                "layer4_modulator": r["layer4_substitution_modulator"],
                "layer5_bias_factor": r["layer5_judgment_bias_factor"],
            }
            for slug, r in regimes.items()
        ]
        st.dataframe(reg_rows, use_container_width=True, hide_index=True)

    st.subheader("Reference figure from the paper")
    fig_path = FIG_DIR / "fig15_layer7_k_sensitivity.png"
    if fig_path.exists():
        st.image(str(fig_path), caption="Figure 4 of the paper — sensitivity of "
                 "the inversion premium of Section 7 to K₇ across three "
                 "jurisdictions, with cross-bloc acquisition variant.",
                 use_container_width=True)
    else:
        st.info("Run scripts/run_layer7.py to regenerate this figure.")
