# What is the code in this directory?

This directory contains mostly deprecated old code from the Feasibility Assessment Phase of
the Biomedical Data Translator project. Breakage of modules in this directory due to
elimination of deprecated downstream dependencies will be noted in this README.md.

As of Oct. 9, 2025, the function `get_ngd_for_all` was
removed from the module `RTX/code/reasoningtool/kg-construction/NormGoogleDistance.py`;
this change breaks a number of modules in this directory. If you need that function,
you can get it from the `NormGoogleDistance.py` module in any older release of
the `RTXteam/RTX` project code.



