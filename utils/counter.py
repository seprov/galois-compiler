#!/usr/bin/env python

import sys
import struct
import ctypes
import array
import pandas
import matplotlib
import matplotlib.pyplot as plt

MAGIC = 0x5a5e5a61
UNSIGNED_SIZE = 4

main_hdr_fmt = struct.Struct('<III')
hdr_fmt = struct.Struct('<IIIIIIIII')

class CounterData(object):
    iteration = None
    work = None
    blocks = None
    tpb = None
    dynsmem = None
    residency = None
    t1 = None
    t2 = None
    
    values = None
    counts = None
    smids = None
    start = None

class QuadArray(object): # read-only
    def __init__(self, a):
        self.a = a

    def __getitem__(self, b):
        low = self.a[b*2]
        high = self.a[b*2+1]
        
        return (high << 32) + low

    def __iter__(self):
        for i in range(0, len(self.a)/2):
            yield self[i]

class CounterFile(object):
    def __init__(self, fs):
        self.fs = fs
        self._hdr_read = False
        self.mblocks = 0
        self.mtpb = 0

    def read(self):
        if not self._hdr_read:
            mh = self.fs.read(main_hdr_fmt.size)
            if not mh:
                print("Unable to read main header", file=sys.stderr)
                yield None

            magic, self.mblocks, self.mtpb = main_hdr_fmt.unpack(mh)
            self.mthreads = self.mblocks * self.mtpb            
            if magic != 0x5a5e5a61:
                print("MAGIC did not match.", file=sys.stderr)
                yield None

        while True:
            x = self.fs.read(hdr_fmt.size)
            if not x:
                break

            zero, iteration, work, blocks, tpb, dynsmem, RES, t1, t2 = hdr_fmt.unpack(x)
            assert zero == 0

            threads = blocks * tpb

            values = array.array('I')
            counts = array.array('I')
            smids = array.array('I')
            start = array.array('I')

            assert values.itemsize == UNSIGNED_SIZE

            smids.fromfile(self.fs, self.mblocks)
            start.fromfile(self.fs, 2*self.mthreads)

            values.fromfile(self.fs, self.mthreads)
            counts.fromfile(self.fs, self.mthreads)

            y = CounterData()
            
            y.iteration = iteration
            y.work = work
            y.blocks = blocks
            y.tpb = tpb
            y.dynsmem = dynsmem
            y.residency = RES
            y.t1 = t1
            y.t2 = t2
            
            y.smids = smids
            y.start = [x for x in QuadArray(start)]
            y.values = values
            y.counts = counts

            yield y

def aggregate_cvs(counts, values, start, span=32, aggcf = sum, aggvf = max, aggsf = min):
    for x in range(0, len(counts), span):
        yield (aggcf(counts[x:x+span]), aggvf(values[x:x+span]), aggsf(start[x:x+span]))

if __name__ == "__main__":
    f = open(sys.argv[1], "r")

    c = CounterFile(f)

    for r in c.read():
        if r is None:
            sys.exit(1)

        
        print('iteration: %d   work: %d' % (r.iteration, r.work))
        for i, (c, v, s) in enumerate(zip(r.counts, r.values, r.start)):
            print(i, c, v, s)
        print()
 
