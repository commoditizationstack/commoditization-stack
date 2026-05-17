"""Tab About — credits, paper citation, repository links."""
import streamlit as st


def render():
    st.header("About")

    st.markdown(
        """
        ### Paper

        **The Cost Gradient of the Build: A Jurisdictionally Structured
        Inversion of Damodaran's Key-Person Discount under Generative AI,
        with a Seven-Layer Framework of the Knowledge-Production Stack
        and the Strategic Reinvention of Innovation-Driven Entrepreneurship**

        *Arthur de Miranda Neto* (2026)
        [LinkedIn](https://www.linkedin.com/in/arthur-mneto/)

        ### Citation (BibTeX)

        ```bibtex
        @misc{demirandaneto2026costgradient,
          title  = {The Cost Gradient of the Build:
                    A Jurisdictionally Structured Inversion of
                    Damodaran's Key-Person Discount under Generative AI},
          author = {de Miranda Neto, Arthur},
          year   = {2026},
          note   = {SSRN preprint}
        }
        ```

        ### Open-source repository

        - GitHub: [commoditization-stack-simulation](https://github.com/ademiran/commoditization-stack-simulation)
        - Author: Arthur de Miranda Neto · [LinkedIn](https://www.linkedin.com/in/arthur-mneto/)
        - License: MIT
        - Documentation: see the project README in the repository.

        ### Acknowledgements

        The framework draws on the work of many cited authors. The author
        thanks colleagues and reviewers whose feedback shaped the framework.

        ### Disclaimer

        This simulator is offered as an open-source companion to the paper.
        All figures and parameter calibrations are illustrative, not
        predictive. The framework is built explicitly to admit user-substituted
        calibrations and alternative scenarios.

        ### Version

        **Simulator v0.9** — May 2026
        """
    )
