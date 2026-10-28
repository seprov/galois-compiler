#!/usr/bin/env python

import perfproc as pp
import sys

t = pp.Table.read_csv(sys.argv[1])
output = sys.argv[2]

for nt in sys.argv[3:]:
    t = t.update(pp.Table.read_csv(nt))

t.write_csv(output)
