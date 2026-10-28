#!/usr/bin/env python

import npreader
import sys
import re
import csv

def out_durations(fd, r):
    x = {}
    x.update(fd)
    p = r['Name'].index("(")
    x['Name'] = r['Name'][:p]
    x['Duration'] = r['Duration']

    return x

#file_re = re.compile("cc-(?P<load>.*)-(?P<totalthreads>[0-9]+).log")
file_re = re.compile("cc-frac-(?P<load>.*)-(?P<totalthreads>[0-9]+).log")
test_cc_re = re.compile('test_cc')

out = []
for x in sys.argv[1:]:
    f = npreader.NVProfReader(open(x, "r"))
    m = file_re.match(x)
    assert m is not None

    fdata = {'load': m.group('load'),
             'totalthreads': m.group('totalthreads')}

    #fdata['load'] = 1.0 * int(fdata['load'])/int(fdata['totalthreads'])

    for r in f.filter_regexp(test_cc_re.match):
        out.append(out_durations(fdata, r))


out.sort(key=lambda x: int(x['load']))

of = sys.stdout

headers = ['load', 'totalthreads', 'Name', 'Duration']

f = csv.DictWriter(of, headers)
f.writeheader()
for r in out:
    f.writerow(r)

        
