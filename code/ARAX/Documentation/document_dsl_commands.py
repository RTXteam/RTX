import sys
import os
import importlib
from tomark import Tomark
import re
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ARAXQuery")
modules = ["ARAX_overlay", "ARAX_filter_kg"]
classes = ["ARAXOverlay", "ARAXFilterKG"]
modules_to_command_name = {'ARAX_overlay': '`overlay()`', 'ARAX_filter_kg': '`filter_kg()`'}
to_print = ""
#for (module, cls) in zip(modules, classes):
#    m = importlib.import_module(module)
#    #print(getattr(m, cls)().describe_me())
#    dsl_name = modules_to_command_name[module]
#    to_print += f"# {module}\n"
#    to_print += f"|{dsl_name} DSL commands\n"
#    for dic in getattr(m, cls)().describe_me():
#        #to_print += Tomark.table([dic])
#        #to_print += "\n"
#        temp_table = Tomark.table([dic])
#        temp_table_split = temp_table.split("\n")
#        better_table = f"|{dsl_name} DSL commands" + ('|' * temp_table_split[0].count('|')) + '\n'
#        better_table += temp_table_split[1] + '-----|\n'
#        better_table += '|**DSL parameters**' + temp_table_split[0] + "\n"
#        better_table += '|**DSL arguments**' + temp_table_split[2] + "\n"
#        to_print += better_table + '\n'

for (module, cls) in zip(modules, classes):
    m = importlib.import_module(module)
    dsl_name = modules_to_command_name[module]
    to_print += f"# {module}\n"
    for dic in getattr(m, cls)().describe_me():
        action = dic['action'].pop()
        del dic['action']
        temp_table = Tomark.table([dic])
        temp_table_split = temp_table.split("\n")
        better_table = "|"+re.sub('\(\)',f'(action={action})', dsl_name) + ('|' * temp_table_split[0].count('|')) + '\n'
        better_table += temp_table_split[1] + '-----|\n'
        better_table += '|_DSL parameters_' + temp_table_split[0] + "\n"
        better_table += '|_DSL arguments_' + temp_table_split[2] + "\n"
        to_print += better_table + '\n'

fid = open('test.md', 'w')
fid.write(to_print)
fid.close()
