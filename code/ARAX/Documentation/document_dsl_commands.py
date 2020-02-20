import sys
import os
import importlib
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ARAXQuery")
modules = ["ARAX_overlay", "ARAX_filter_kg"]
classes = ["ARAXOverlay", "ARAXFilterKG"]
for (module, cls) in zip(modules, classes):
    m = importlib.import_module(module)
    print(getattr(m, cls)().describe_me())
