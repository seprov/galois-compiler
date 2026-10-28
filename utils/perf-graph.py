#!/usr/bin/env python

import perfproc as pp
import sys
import argparse
from asq.initiators import query
import matplotlib.pyplot as plt


def autolabel(rects, prevrects):
    if not args.ymax:
        return

    for i, r in enumerate(rects):
        h = r.get_height()
        if h >= args.ymax:
            if prevrects and prevrects[i].get_height() > args.ymax:
                hmult = 1.05 # BUGGY
            else:
                hmult = 1.01

            ax.text(r.get_x()+width/2, hmult*args.ymax, '%0.2f'%(h,),
                    ha='center', va='bottom')

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
parser.add_argument("--sip", action="store_true", default = False, help="Strip category label from input name")
parser.add_argument("--rot", type=float, default = 0, help="Rotation for xticklabel")
parser.add_argument("--vorder", action="append", help="Variant ordering")
parser.add_argument("-o", dest="output", help="Output file")

def vorder(v):
    if args.vorder:
        return args.vorder.index(v)
    else:
        return v

args = parser.parse_args()

t = pp.Table.read_csv(args.input)

x = query(t.rows)

if args.bmk:    
    x = x.where(lambda x: x[pp.BMK] in set(args.bmk))

if args.nobmk:    
    x = x.where(lambda x: x[pp.BMK] not in set(args.nobmk))

if args.novar:
    w = [j for j in args.novar if "+" not in j]
    if len(w):
        print("Incorrect parameters for --nv", ",".join(w), file=sys.stderr)
        sys.exit(1)

    novar = set([tuple(j.split("+")) for j in args.novar])

    x = x.where(lambda x: (x[pp.BMK], x[pp.BMK_VARIANT]) not in novar)


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

if args.multi and len(varperbmk) == 1:
    k = list(varperbmk.keys())[0]
    if len(varperbmk[k]) > 1:
        #print [(x[0], x[2], vorder(x[2])) for x in out]

        out.sort(key=lambda x: (x[0], vorder(x[2])))

fig, ax = plt.subplots()
width = 0.35

if args.multi:
    assert len(varperbmk) == 1
    k = list(varperbmk.keys())[0]
    numvar = len(varperbmk[k])
    numinp = len(query(out).distinct(lambda x: x[0]).to_list())
    width = 1.0/(numvar+1)
    ind = [float(i) - (width*numvar)/2 for i in range(numinp)]

    oout = out
    colors = ['r', 'b', 'g', 'y', 'cyan']
    l = []
    pr = None
    for i in range(numvar):
        out = oout[i::numvar]
        val = [x[1] for x in out]
        if len(val) < len(ind):
            val += [0] * (len(ind) - len(val))

        rects1 = ax.bar(ind, val, width, color=colors.pop())
        autolabel(rects1, pr)
        pr = rects1
        l.append((rects1[0], out[0][2]))
        ind = [x + width for x in ind]

    ax.set_xticks([i for i in range(numinp)])
    ax.legend([ll[0] for ll in l], [ll[1] for ll in l], loc="best")
else:
    ind = list(range(len(out)))
    val = [x[1] for x in out]

    rects1 = ax.bar(ind, val, width)
    ax.set_xticks([i+width/2 for i in ind])

if args.ylabel: ax.set_ylabel(args.ylabel)
if args.xlabel: ax.set_xlabel(args.xlabel)
if args.title: ax.set_title(args.title)
if args.ymax: ax.set_ylim(0, args.ymax)


ax.set_xticklabels( [x[0] for x in out], rotation=args.rot, ha = 'center' if args.rot == 0 else 'right')

if args.hl:
    for i in args.hl:
        plt.axhline(i, linestyle='--', color='r') #TODO

if args.yg:
    ax.yaxis.grid()

if args.rot != 0:
    plt.subplots_adjust(bottom=0.35,left=0.23)

#ax.legend( (rects1[0]), (args.prefix,) )

if not args.output:
    plt.show()
else:
    fig.savefig(args.output, bbox_inches='tight')
