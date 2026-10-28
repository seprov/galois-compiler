#!/usr/bin/env python
import sys
import argparse
import re

parser = argparse.ArgumentParser(description="Extract record that match")


parser.add_argument("regex", help="Regular expression")
parser.add_argument("input", help="Input file")
parser.add_argument("-v",  dest="invert", default=False, action="store_const", const=True, help="Invert match")

args = parser.parse_args()

r = re.compile(args.regex)

for i, l in enumerate(open(args.input, "r")):
    if i == 0:
        sys.stdout.write(l)
        continue

    m = r.search(l)
    if (m is not None) ^ (args.invert == True):
        sys.stdout.write(l)

    
