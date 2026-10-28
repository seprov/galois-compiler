#!/usr/bin/env python

import perfproc as pp
import csv
import sys
import re
import argparse
import datetime
import perfproc

TIME_FMT = "%Y-%m-%d %H:%M:%S"

parser = argparse.ArgumentParser(description="Extract performance date from a log file to a CSV")

parser.add_argument("input", nargs="+", help="Input file")

parser.add_argument("-o", dest="output", metavar="FILE", 
                    default="/dev/stdout", help="Output file")

parser.add_argument("-s", dest="suite", help="Suite")

parser.add_argument("--xid", dest="xid", help="Experiment ID")

args = parser.parse_args()

st = re.compile("^START")
dt = re.compile("^DATE")
pd_begin = re.compile("^PERFDATE BEGIN_RUN")
pd_end = re.compile("^PERFDATE END_RUN")
p = re.compile("^PERF ")

T = pp.Table([])

mix = {}
if args.suite:
    mix[pp.SUITE] = args.suite

if args.xid:
    mix[pp.EXP_ID] = args.xid
START_DATE = None
END_DATE = None

for i in args.input:
    of = open(i, "r")
    for l in of:        
        m = st.match(l)
        if m:
            assert False, l
            print(m.group(0))
            continue

        m = dt.match(l)
        if m:
            mix["date_exp"] = l.strip().split(" ", 2)[2]
            if START_DATE is None:
                START_DATE = mix["date_exp"]
            else:
                START_DATE = min(START_DATE, mix["date_exp"])
            continue

        m = pd_begin.match(l)
        if m:
            mix["date_run_begin"] = l.strip().split(" ", 2)[2]
            continue

        m = pd_end.match(l)
        if m:
            mix["date_run_end"] = l.strip().split(" ", 2)[2]
            END_DATE = max(END_DATE, mix["date_run_end"])
            continue
        
        m = p.match(l)
        if m:
            ls = l.strip().split(" ", 6)
            out = {}
            out[pp.BMK] = ls[1]
            out[pp.BMK_VARIANT] = ls[2]
            out[pp.INPUT] = ls[3]
            out[pp.RUN] = ls[4]
            out[pp.TIME_NS] = ls[5]
            out[pp.CMDLINE] = ls[6]
            #TODO: system, time, commandline, etc.

            if mix:
                out.update(mix)

            T.rows.append(out)


T.write_csv(args.output)
print("Total time for experiment (h:m:s)", datetime.datetime.strptime(END_DATE, TIME_FMT) - datetime.datetime.strptime(START_DATE, TIME_FMT), file=sys.stderr)
