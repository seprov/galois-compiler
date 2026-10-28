#!/usr/bin/env python

import sys
import perfproc as pp

input_xlat = {'25k': 'mesh/25k',
              '250k': 'mesh/250k',
              'grid': 'grid/2d-2e20', 
              'FLA': 'road/FLA', 
              'USA': 'road/USA', 
              'NY': 'road/NY',
              'CAL': 'road/CAL',              
              '1M': 'mesh/r1M', 
              'random': 'random/r4-2e23', 
              'random-r4-2e23': 'random/r4-2e23', 
              '5M': 'mesh/r5M', 
              'rmat12': 'rmat/rmat12', 
              'rmat22': 'rmat/rmat22'}

xlat_dest = set(input_xlat.values())

def cvt_input(row):
    if row['input_name'] not in input_xlat:
        assert row['input_name'] in xlat_dest, row['input_name']
        return row['input_name']

    return input_xlat[row["input_name"]]

if len(sys.argv) < 2:
    print "Usage: %s processed-input.dat"  % (sys.argv[0],)
    sys.exit(0)

t = pp.Table.read_csv(sys.argv[1])

for r in t.rows:
    r["input_name"] = r[pp.INPUT]
    del r[pp.INPUT]

t.add_columns({pp.INPUT: cvt_input})

t.write_csv(sys.argv[1])
