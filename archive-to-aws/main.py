#!/usr/bin/python

import create
import archive
import sys


if len(sys.argv) < 2:
    s =  "Usage: \n"
    s += "\t{0} {1}\n".format(sys.argv[0], create.usage())
    sys.exit(s)

if sys.argv[1] == "create":
    a = archive.archive(sys.argv[2])
    a.create()
