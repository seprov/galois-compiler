#!/usr/bin/env python

import sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.style.use('ggplot')

files = sys.argv[1:]

group_by_field = "Kernel"

df = [pd.read_csv(f) for f in files]

grouped = []
groups = set()
for ddf in df:
    grouped.append(ddf.groupby(group_by_field))
    for group, data in grouped[-1]:
        groups.add(group)


for gg in groups:
    out = []
    for g in grouped:
        if gg in g.groups:
            x = g.get_group(gg)
            out.append(x)

    if len(out) != len(files):
        print "%s not in all files" % (gg,)
    else:
        #'L2 Hit Rate (L1 Reads)'
        #'Device Memory Read Transactions'
        for col in ['L2 Hit Rate (L1 Reads)']:
            ser = [pd.Series(list(v[col])) for v in out]
            x = pd.DataFrame(dict([(f, s) for f, s in zip(files, ser)]))
            p = x.plot(title=gg, style='.-')
            p.set_ylabel(col)
            p.set_xlabel('Invocation')

plt.show()
