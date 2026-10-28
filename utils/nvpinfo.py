#!/usr/bin/env python

import npreader
import sys
import re
import csv
import os

keys_interested = set(['Duration', 'Kernel'])

def out_durations(fd, r, kf):
    def get_name(rr):
        if 'Name' in r:
            f = 'Name'
        else:
            f = 'Kernel'
           
        if f not in kf:
            kf.add(f)
        
        p = r[f].find("(")
        if p >= 0:
            x[f] = r[f][:p]
        
    x = {}
    x.update(fd)
    get_name(r)

    for k in keys_interested:
        if k in r and k not in x:
            x[k] = r[k]
            if k not in kf: 
                kf.add(k)
            
    return x

for x in sys.argv[1:]:
    out = []
    hdrs = set()

    of, ext = os.path.splitext(x)
    of = of + ".csv"
    if os.path.exists(of):
        print(of, "exists, not processing", x, file=sys.stderr)

    f = npreader.NVProfReader(open(x, "r"))

    keys_interested = set()
    fdata = {}
    for r in f.records():
        if len(keys_interested) == 0:
            keys_interested = set(f.headers)

        out.append(out_durations(fdata, r, hdrs))

    headers = hdrs
    f = csv.DictWriter(open(of, "w"), headers)
    f.writeheader()
    for r in out:
        f.writerow(r)
    
