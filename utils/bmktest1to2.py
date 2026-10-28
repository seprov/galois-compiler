#!/usr/bin/env python

import sys
import argparse
import os

PERF_RE = "^Total time: (?P<time_ns>.*) ns$"

class bmktest1(object):
    bmk = None
    variant = None
    INPUTS = None
    PERF_RE = None
    PRODUCES_OUTPUT_FILE = False

    def _get_output(self):
        if self.PRODUCES_OUTPUT_FILE:
            return ["x.set_arg('-o')", 
                    "x.set_arg('@output', bmk2.AT_TEMPORARY_OUTPUT)"
                    ]

    def _get_input(self):
        for i, d in self.INPUTS.items():
            if 'input' in d:
                if isinstance(d['input'], str):
                    return "x.set_arg(bmkinput.props.file, bmk2.AT_INPUT_FILE)"
                else:
                    return "x.set_arg(bmkinput.props.file, bmk2.AT_INPUT_FILE) #FIXTHIS %s" % (d['input'],)
            
    def _get_checker(self):
        for i, d in self.INPUTS.items():
            if 'output' in d:
                if 'comp' in d:
                    if d['comp'] == "regex":
                        return "x.set_checker(bmk2.REChecker('%s' %% (FIXTHIS,)))" % (d['output'].pattern)            
                    elif d['comp'] == "pass":
                        # 
                        return "x.set_checker(FIXTHIS)"
                    elif d['comp'] == "checker":
                        return "x.set_checker(bmk2.ExternalChecker(FIXTHIS))"
                    else:
                        assert False, d['comp']
                else:
                    assert self.PRODUCES_OUTPUT_FILE
                    return "x.set_checker(bmk2.DiffChecker('@output', bmkinput.props.%s_output))" % (self.bmk,)            
            else:
                if 'comp' in d:
                    if d['comp'] == "checker":
                        return "x.set_checker(bmk2.ExternalChecker(FIXTHIS))"
                    else:
                        assert False, d

                assert False, d

    def _get_perf(self):
        if self.PERF_RE is not None:
            if self.PERF_RE.pattern == PERF_RE:
                return "x.set_perf(bmk2.PerfRE(PERF_RE))"
            else:
                return "x.set_perf(bmk2.PerfRE('%s'))" % (self.PERF_RE.pattern)

        return ""

    def _get_input_bispec(self):
        out = []
        for i, d in self.INPUTS.items():
            if 'input' in d:
                if isinstance(d['input'], str):
                    n = os.path.basename(d['input'])
                    if n[-3:] == ".gr": n = n[:-3]
                    out.append(n)
                else:
                    out.append(str(d['input']))
                

        return "#%s %s" % (self.bmk, ",".join(out))

    def _get_input_filter(self):
        fmt = ""
        flags = set()

        for i, d in self.INPUTS.items():
            if 'input' in d:
                if d['input'][-3:] == ".gr":
                    fmt = "bin/galois"
                else:
                    fmt = "FIXTHIS"
                    print("WARNING: Unknown input format", (d['input']), file=sys.stderr)
                
                if '.sym.' in d['input']:
                    flags.add('symmetric')

        #flags = set(["symmetric", "triangle"])
        flag_cond = " and ".join(["'%s' in x.props.flags" % (f,) for f in flags])
        if flag_cond == "": flag_cond = "len(x.props.flags) == 0"

        assert fmt != ""

        fmt_cond = "x.props.format == '%s'" % (fmt)
        cond = fmt_cond
        if flag_cond: cond += " and " + flag_cond

        return "return filter(lambda x: %s" % (cond,) + ", inputs)"

    def to2(self, f):
        if self.bmk in self.variant:
            idfy = self.variant
        else:
            idfy = (self.bmk + "_" + self.variant)

        idfy = idfy.replace("-", "_")

        x = self._get_input_filter()

        print("import bmk2", file=f)
        print("from irglprops import irgl_bmk, PERF_RE", file=f)
        print("", file=f)
        print("class %s(irgl_bmk):" % (idfy), file=f)
        print("\tbmk = '%s'" % (self.bmk,), file=f)
        print("\tvariant = '%s'" % (self.variant,), file=f)
        print("", file=f)
        print("\tdef filter_inputs(self, inputs):", file=f)
        print("\t\t" + x, file=f)
        print("", file=f)
        print("\tdef get_run_spec(self, bmkinput):", file=f)
        print("\t\tx = bmk2.RunSpec(self, bmkinput)", file=f)
        print("\t\tx.set_binary(self.props._cwd, 'test')", file=f)
        x = self._get_input()
        if x: print("\t\t" + x, file=f)

        x = self._get_output()
        if x is not None:
            for l in x:
                print("\t\t" + l, file=f)

        print("\t\t" + self._get_checker(), file=f)
        print("\t\t" + self._get_perf(), file=f)
        print("\t\treturn x", file=f)
        print("", file=f)
        print(self._get_input_bispec(), file=f)
        print("BINARIES = [%s()]" % (idfy), file=f)

def load_py_module(f):
    g = {'__file__': f}
    x = exec(compile(open(f, "rb").read(), f, 'exec'), g)
    return g
   

parser = argparse.ArgumentParser("Convert bmktest.py to bmktest2.py (partial)")
parser.add_argument("source", help="Source to convert")

args = parser.parse_args()

mod = load_py_module(args.source)
x = bmktest1()
x.bmk = mod['BMK_NAME']
x.variant = mod['BMK_VARIANT']
x.INPUTS = mod['INPUTS']
x.PERF_RE = mod['PERF_RE'] if 'PERF_RE' in mod else None
x.PRODUCES_OUTPUT_FILE = mod['PRODUCES_OUTPUT_FILE']

x.to2(sys.stdout)
