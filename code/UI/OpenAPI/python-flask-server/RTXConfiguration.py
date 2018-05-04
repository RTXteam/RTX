#!/usr/bin/python3

import re
import os
import sys
import datetime

class RTXConfiguration:

  #### Constructor
  def __init__(self):
    self.version = "RTX 0.4.1"


  #### Define attribute version
  @property
  def version(self) -> str:
    return self.version

  @version.setter
  def version(self, version: str):
    self._session = version


def main():
  rtxConfig = RTXConfiguration()
  print("RTX Version string: " + rtxConfig.version)


if __name__ == "__main__": main()
