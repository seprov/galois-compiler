#!/usr/bin/env python

import perfproc
import sys
import argparse

parser = argparse.ArgumentParser(description="Compare performance date")

parser.add_argument("input", help="Input file")
parser.add_argument("baseline", help="Baseline file")
parser.add_argument("output", default="-", help="Output file")

parser.add_argument("-b", "--normalize-best", dest="action", default="normalize-best", action="store_const", const="normalize-best", help="Find best benchmark from baseline and normalize to that")

parser.add_argument("-s", "--normalize-self", dest="action", default="normalize-self", action="store_const", const="normalize-self", help="Compare before and after")

args = parser.parse_args()

inp = perfproc.Table.read_csv(args.input)

baseline = perfproc.Table.read_csv(args.baseline)

if args.action == "normalize-best":
    a = perfproc.Analysis(inp)
    b = perfproc.Analysis(baseline)

    best = b.fastest_variant()
    #best.print_list()
    n =  a.normalize_suite_perf(best)
if args.action == "normalize-self":
    a = perfproc.Analysis(inp)
    b = perfproc.Analysis(baseline)

    p = b.suite_perf()
    n = a.normalize_suite_perf_to_prev(p)

n.write_csv(args.output)
