#!/usr/bin/env python

import perfproc as pp
import sys
import argparse
from asq.initiators import query
import ssg
import csv

parser = argparse.ArgumentParser(description="Produce a barchart from output of perf-merge.py")

parser.add_argument("input", help="Input file which will be graphed")
parser.add_argument("column_prefix", help="Plot values from column prefix")
parser.add_argument("--title", metavar="TITLE", help="Plot title")
parser.add_argument("--ylabel", metavar="LABEL", help="Y-axis label")
parser.add_argument("--xlabel", metavar="LABEL", help="X-axis label")
parser.add_argument("--ymax", metavar="NUM", type=float, help="Y-axis maximum limit")
parser.add_argument("--yg", action="store_true", default=False, help="Draw grid on y-axis")
#parser.add_argument("--ymin", metavar="NUM", type=float, help="Y-axis minimum limit")
parser.add_argument("--multi", action="store_true", default=False, help="multiple series")
parser.add_argument("--hl", metavar="NUM", type=float, help="Horizontal X-axis line at NUM", action="append")
parser.add_argument("-b", dest="bmk", metavar="BMK", action="append", help="Plot BMK only")
parser.add_argument("--nb", dest="nobmk", metavar="BMK", action="append", help="Do not plot BMK")
parser.add_argument("--nv", dest="novar", metavar="BMKVAR", action="append", help="Do not plot BMK VARIANT (specify as BMK+VARIANT)")
parser.add_argument("--ni", dest="noinp", metavar="INPUT", action="append", help="Do not plot INPUT")
parser.add_argument("--sip", action="store_true", default = False, help="Strip category label from input name")
parser.add_argument("--rot", type=float, default = 0, help="Rotation for xticklabel")
parser.add_argument("--vorder", action="append", help="Variant ordering")
parser.add_argument("--hatches", action="append", help="Hatch")
parser.add_argument("-w", dest="width", help="Width (inches)")
parser.add_argument("--ht", dest="height", help="Height (inches)")
parser.add_argument("-o", dest="output", help="Output file")
parser.add_argument("-p", dest="palette", help="Palette CSV")


def read_palette(pfile):
    f = csv.DictReader(open(pfile, "r"))
    out = {}
    for rec in f:
        for i in rec:
            if rec[i] == "":
                rec[i] = None

        out[rec['series']] = rec

    return out   

def vorder(v):
    if args.vorder:
        return args.vorder.index(v)
    else:
        return v

args = parser.parse_args()

PAL = None
if args.palette:
    PAL = read_palette(args.palette)

t = pp.Table.read_csv(args.input)

x = query(t.rows)

if args.bmk:    
    x = x.where(lambda x: x[pp.BMK] in set(args.bmk))

if args.nobmk:    
    x = x.where(lambda x: x[pp.BMK] not in set(args.nobmk))

if args.novar:
    w = [j for j in args.novar if "+" not in j]
    if len(w):
        print >>sys.stderr, "Incorrect parameters for --nv", ",".join(w)
        sys.exit(1)

    novar = set([tuple(j.split("+")) for j in args.novar])

    x = x.where(lambda x: (x[pp.BMK], x[pp.BMK_VARIANT]) not in novar)

if args.noinp:
    x = x.where(lambda x: x[pp.INPUT] not in set(args.noinp))

if args.column_prefix == "nil":
    col_name = pp.AVG_TIME_NS_NORM
else:
    col_name = args.column_prefix + "/" + pp.AVG_TIME_NS_NORM

x = x.select(lambda x: (x[pp.BMK], x[pp.BMK_VARIANT], x[pp.INPUT], x[col_name])).order_by(lambda x: (x[0], vorder(x[1]), x[2])).to_list()

varperbmk = dict(query(x).group_by(lambda j: j[0], lambda j: j[1], lambda k, v: (k, set(v))))

out = []
for i in x:    
    if i[3] != "":
        y = float(i[3])
    else:
        y = 0

    bmk, var, inp = i[0], i[1], i[2]
    if args.sip and "/" in inp:
        inp = inp[inp.rindex("/")+1:]

    if len(varperbmk) == 1:
        if len(varperbmk[bmk]) > 1:
            if args.multi:
                out.append(("%s" % (inp), y, var))
            else:
                out.append(("%s-%s" % (var, inp), y))
        else:
            out.append(("%s" % (inp,), y))
    else:
        if len(varperbmk[bmk]) > 1:
            out.append(("%s-%s-%s" % (bmk, var, inp), y))
        else:
            out.append(("%s-%s" % (bmk, inp), y))

if args.multi:
    series = []

    for s in varperbmk.values()[0]:        
        xyv = [o for o in out if o[2] == s]
        S = ssg.Series([i[0] for i in xyv], [i[1] for i in xyv], s)
        if args.hatches and S.title in args.hatches:
            print S.title
            S.hatch = "auto"

        series.append(S)

    series.sort(key=lambda x: vorder(x.title))
else:
    series = [ssg.Series([x[0] for x in out], [x[1] for x in out], "")]

b = ssg.Barchart(series)
b.axis.x.title = args.xlabel
b.axis.x.tickstyle.rotation = args.rot

b.axis.y.title = args.ylabel
b.title = args.title
b.axis.y.maximum = args.ymax

b.width = args.width
b.height = args.height

if args.multi:
    b.legend.visible = True
    b.legend.location = 'best'

if args.rot != 0: b.axis.x.tickstyle.ha = 'right'

if PAL:
    for s in b.series:
        if s.title in PAL:
            p = PAL[s.title]
            s.color = p['color']
            s.hatch = p['hatch']

b.plot()

if args.yg:
    b.ax.yaxis.grid()

#if args.rot != 0:
#    ssg.plt.subplots_adjust(bottom=0.35, left=0.23)

if args.hl:
    for i in args.hl:
        ssg.plt.axhline(i, linestyle='--', color='r') #TODO

if args.ymax:
    b.label_cutoff()

if not args.output:
    b.show()
else:
    b.save(args.output)


