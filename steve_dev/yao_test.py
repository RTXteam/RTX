import sys
from yao_mod.Orangeboard import Orangeboard


if "--test" in set(sys.argv):
    Orangeboard.test()
