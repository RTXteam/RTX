#!/usr/bin/python3

import re
import os
import sys
import datetime

class RTXConfiguration:

	#### Constructor
	def __init__(self):
		self.version = "RTX 0.4.1"

		# This is the flag/property to switch between the two containers
		self.live = "Production"
		#self.live = "KG2"

		if self.live == "Production":
			self.bolt = "bolt://rtx.ncats.io:7687"
			self.database = "rtx.ncats.io:7474/db/data"

		if self.live == "KG2":
			self.bolt = "bolt://rtx.ncats.io:7787"
			self.database = "rtx.ncats.io:7574/db/data"



	#### Define attribute version
	@property
	def version(self) -> str:
		return self._version

	@version.setter
	def version(self, version: str):
		self._version = version


def main():
	rtxConfig = RTXConfiguration()
	print("RTX Version string: " + rtxConfig.version)
	print("live version: %s" % rtxConfig.live)
	print("bolt protocol: %s" % rtxConfig.bolt)
	print("database: %s" % rtxConfig.database)


if __name__ == "__main__": main()
