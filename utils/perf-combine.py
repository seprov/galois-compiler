#!/usr/bin/env python

import perfproc as pp
import sys

t = pp.Table([])
for i in sys.argv[1:]:
    t = t.combine(pp.Table.read_csv(i))

t.write_csv("/dev/stdout")
