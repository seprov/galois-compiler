#!/usr/bin/env python

import perfproc as pp
import sys
import argparse
from asq.initiators import query

parser = argparse.ArgumentParser(description="Produce data suitable for a barchart")

parser.add_argument("input", nargs="+", help="Input files which will be outer-joined")
parser.add_argument("-p", dest="prefix", help="Input prefixes", action="append")
parser.add_argument("-o", dest="output", help="Output file", default="-")

args = parser.parse_args()

assert len(args.input) == len(args.prefix) + 1

t = []
for i in args.input:
    t.append(pp.Table.read_csv(i))


out = t[0].merge(t[1], args.prefix[0])
for i in range(2, len(args.input)):
    out = out.merge(t[i], args.prefix[i - 1])

out.write_csv(args.output)

