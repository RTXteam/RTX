import sys
import os
import importlib
from tomark import Tomark
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ARAXQuery")
modules = ["ARAX_overlay", "ARAX_filter_kg"]
classes = ["ARAXOverlay", "ARAXFilterKG"]
to_print = ""
for (module, cls) in zip(modules, classes):
    m = importlib.import_module(module)
    #print(getattr(m, cls)().describe_me())
    to_print += f"#{module}\n"
    for dic in getattr(m, cls)().describe_me():
        to_print += Tomark.table([dic])
        to_print += "\n"

fid = open('test.md', 'w')
fid.write(to_print)
fid.close()

