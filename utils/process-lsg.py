#!/usr/bin/env python

import sys
import perfproc as pp

input_xlat = {'../../inputs/25k': 'mesh/25k',
              '../../inputs/250k.2': 'mesh/250k',
              '../../inputs/2d-2e20.sym.gr': 'grid/2d-2e20', 
              '../../inputs/USA-road-d.NY.gr': 'road/NY',
              '../../inputs/USA-road-d.NY.sym.gr': 'road/NY', #TODO
              '../../inputs/USA-road-d.CAL.gr': 'road/CAL',
              '../../inputs/USA-road-d.CAL.sym.gr': 'road/CAL', #TODO
              '../../inputs/USA-road-d.FLA.sym.gr': 'road/FLA', 
              '../../inputs/USA-road-d.USA.gr': 'road/USA', 
              '../../inputs/USA-road-d.USA.sym.gr': 'road/USA', 
              '../../inputs/r1M': 'mesh/r1M', 
              '../../inputs/r4-2e23.gr': 'random/r4-2e23', 
              '../../inputs/r5M': 'mesh/r5M', 
              '../../inputs/rmat12.sym.gr': 'rmat/rmat12', 
              '../../inputs/rmat22.gr': 'rmat/rmat22'}

bmk_xlat = {'bfs': ('bfs', 'topo'), 
            'bfs-atomic': ('bfs', 'topo-atomic-unroll'),
            'bfs-merrill': ('bfs', 'merrill'), 
            'bfs-wla': ('bfs', 'wla'), 
            'bfs-wlc': ('bfs', 'wlc'),
            'bfs-wlw': ('bfs', 'wlw'), 
            'dmr': ('dmr', 'dmr'), 
            'mst': ('mst', 'topo'), 
            'sssp': ('sssp', 'topo'), 
            'sssp-wlc': ('sssp', 'wlc'), 
            'sssp-wln': ('sssp', 'wln')}

def cvt_input(row):
    return input_xlat[row[pp.INPUT_FILE]]

def cvt_bmk_bmk(row):
    return bmk_xlat[row["benchmark"]][0]

def cvt_bmk_variant(row):
    return bmk_xlat[row["benchmark"]][1]

if len(sys.argv) < 3:
    print "Usage: %s processed-input.dat processed-output.csv"
    sys.exit(0)

t = pp.read_table_file(sys.argv[1], headers = [pp.RUN, "benchmark", "variant", pp.TIME_MS, pp.INPUT_FILE])

t.add_time_ns().add_columns({pp.SUITE: 'lsg2', pp.EXP_ID: 'lsg2-numbers', pp.INPUT: cvt_input, pp.BMK: cvt_bmk_bmk, pp.BMK_VARIANT: cvt_bmk_variant})

t.write_csv(sys.argv[2])
