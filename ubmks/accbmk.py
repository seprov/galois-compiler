#!/usr/bin/env python

import sys
from asq.initiators import query
import math
import scipy.stats
from ssg import *

def stats(a, sample=True):
    n = len(a)

    avg = 1.0*sum([aa for aa in a])/n
    v = sum([(aa - avg)**2 for aa in a])

    if sample:
        v /= (n - 1)
    else:
        v /= n

    stdev = math.sqrt(v)

    return avg, v, stdev

def ci(n, mean, stdev, alpha=0.95):
    if n < 30:
        i_alpha = scipy.stats.t.interval(alpha, n - 1)[1]
    else:
        i_alpha = scipy.stats.norm.interval(alpha)[1]

    diff = i_alpha * stdev / math.sqrt(n)

    return (mean - diff, mean + diff)


def av(k, g):
    out = [k]

    for i in range(1, len(g[0])):
        #avg, v, stdev = stats([v[i] for v in g])
        n, (mi, mx), avg, v, skew, kurt = scipy.stats.describe([v[i] for v in g])
        sd = math.sqrt(v)

        ci_low, ci_high = ci(n, avg, sd)

        out.append(avg)
        out.append(v)
        out.append(sd)
        out.append(ci_high - avg)

    return out

f = open(sys.argv[1])

out = []
for l in f:
    ls = l.strip().split()
    if len(ls) == 4:
        out.append(list(map(int, ls)))

l = query(out).group_by(lambda x: x[0], result_selector = av).to_list()
for ll in l:
    print(" ".join([str(x) for x in ll]))


X = [x[0] for x in l]
s1 = Series(X, [x[1]/1000000 for x in l], "Baseline", yerr=[x[4]/1000000 for x in l])
s2 = Series(X, [x[5]/1000000 for x in l], "Cooperative", yerr=[x[8]/1000000 for x in l])
s3 = Series(X, [x[9]/1000000 for x in l], "Cooperative (Auto)", yerr=[x[12]/1000000 for x in l])

P = XYPlot([s2, s3])
P.legend.visible = True
P.legend.location = 'best'
P.axis.x.minimum=0
P.axis.y.title = 'Runtime (ms)'
P.axis.x.title = 'Pushes'
P.plot()
P.show()
