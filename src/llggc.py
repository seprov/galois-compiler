#!/usr/bin/env python
# -*- mode: python -*-
# Low-level driver

import sys
import sys
if sys.version_info < (2, 7):
    print >>sys.stderr, "%s: need python version 2.7 (you have %s)" % (sys.argv[0], sys.version)
    sys.exit(1)

import argparse
import os
import gg.compiler
from gg.passes.astmisc import CFG2DOTPass, RunDOTPass, ASTDumperPass, STDumperPass, STWalkerPass

def add_backend_options(p):
    config = gg.compiler.get_config()
    backends = config['backends']

    for b in backends:
        backends[b].add_backend_arguments(p)

parser = argparse.ArgumentParser(description="Compile a Galois program to the GPU")

parser.add_argument("input", help="Input file")

parser.add_argument("--vis-cfg", dest="vis_cfg", metavar="PREFIX", help="Output a visualization of the CFG to PREFIX-kernel.dot")

parser.add_argument("--dot", dest="run_dot", action="store_const", const=True, default=False, help="Run dot on CFG files")

#parser.add_argument("--ann", dest="ann", action="append", choices=["rwsets", "_cblocks"], help="Run specified AST annotation pass")

parser.add_argument("--dfa", dest="dfa", action="append", choices=["dom", "focal"], help="Run specified DFA")

parser.add_argument("--dump-ast", dest="dump_ast",  action="store_true", help="Dump AST")

parser.add_argument("--dump-syms", dest="dump_syms",  action="store_true", help="Dump Symbols")

parser.add_argument("--walk-syms", dest="walk_syms",  action="store_true", help="Walk AST and dump symbols")

parser.add_argument("-o", dest="output", metavar="FILE", help="Output file")

parser.add_argument("-b", dest="backend", help="Backend", default="cuda", choices=set(["cuda"]))

add_backend_options(parser)


args = parser.parse_args()
opts = gg.compiler.CompilerOptions(backend = args.backend)
comp = gg.compiler.Compiler()
opts.backend.set_options(args)
passes = []

if args.vis_cfg:
    passes.append(CFG2DOTPass(args.vis_cfg))

    if args.run_dot:
        passes.append(RunDOTPass())

if args.dump_ast:
    passes.append(ASTDumperPass())

if args.dump_syms:
    passes.append(STDumperPass())

if args.walk_syms:
    passes.append(STWalkerPass())

if args.dfa:
    import gg.passes.dfa

    for an in args.dfa:
        if an == "dom":
            passes.append(gg.passes.dfa.DominatorsAnalysis(True))
        elif an == "focal":
            passes.append(gg.passes.dfa.FocalPointsAnalysis(True))


if not comp.compile(args.input, args.output, opts, passes):
    sys.exit(1)



