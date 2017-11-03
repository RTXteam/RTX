import sys
from yao_mod.Orangeboard import Orangeboard
from yao_mod import ReasoningTool


if "--test" in set(sys.argv):
    Orangeboard.test()
    ReasoningTool.test()
