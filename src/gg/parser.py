#!/usr/bin/env python

import sys
import os

def parse(f):
    # TODO: possibly pass in a standard set of imports?
    g = {}
    x = execfile(f, g)
    return g['ast']

Import = parse

if __name__ == "__main__":
    print parse(sys.argv[1])
