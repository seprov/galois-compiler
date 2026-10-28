#!/usr/bin/env python
import sys
sys.path.append(".")
import os
import subprocess
import argparse
import tempfile
import re
import datetime

if not hasattr(subprocess, "check_output"):
    print >>sys.stderr, "%s: Need python 2.7" % (sys.argv[0],)
    sys.exit(1)

TIME_FMT = "%Y-%m-%d %H:%M:%S"

def split_decimal_str(n):
    p = n.find(".")
    if p != -1:
        whole = int(n[:p])
        frac = int(n[p+1:])
    else:
        whole = int(n)

    return (whole, frac)

def run_command(cmd, stdout = True, stderr = True):    
    if stderr:
        stdout = True
        stderrh = subprocess.STDOUT
    else:
        stderrh = None

    output = None
    error = None

    if stdout:
        try:
            output = subprocess.check_output(cmd, stderr=stderrh)
            rv = 0
        except subprocess.CalledProcessError as e:
            print >>sys.stderr, "Execute failed: " + " ".join(cmd)
            output = e.output
            rv = e.returncode
        except OSError as e:
            print >>sys.stderr, "Execute failed: " + " ".join(cmd)
            output = e.strerror
            rv = e.errno
            if e.errno == 2:
                output += " (are you running this in gensrc/?)"
    else:
        rv = subprocess.call(cmd, stderr=stderrh)

    return (rv, output, error)

def run_diff_test(file1, gold, quiet=True):
    #TODO:  check that gold exists
    diff = ['diff', '-q', file1, gold]
    rv, stdout, stderr = run_command(diff)

    return rv, stdout, stderr

def run_checker_test(cmd_line, quiet=True):
    rv, stdout, stderr = run_command(cmd_line)

    return rv, stdout, stderr

def run_regex_test(output, reo):
    if reo.flags & re.MULTILINE:
        m = reo.search(output)
        if m: return 0
    else:
        mlo = output.split("\n")
        for l in mlo:
            m = reo.search(l)
            if m: return 0
            
    return 1 # unix style return value

class Run(object):
    def __init__(self, bmk_spec, inp):
        self.spec = bmk_spec
        self.bmk_name = bmk_spec.BMK_NAME
        self.bmk_variant = bmk_spec.BMK_VARIANT
        self.params = bmk_spec.INPUTS[inp]
        self.input = self.params['name']

        self.retval = -1
        self.stdout = ""
        self.stderr = ""

        self.check_retval = -1
        self.check_stdout = ""
        self.check_stderr = ""

        self.tmpfile = None

    def run(self):
        if self.spec.PRODUCES_OUTPUT_FILE:
            th, self.tmpfile = tempfile.mkstemp(prefix="ggc-test-")
            self.cmd_line = self.spec.build_cmd_line(self.params, self.tmpfile)
        else:
            self.cmd_line = self.spec.build_cmd_line(self.params)

        self.cmd_line_c = " ".join(self.cmd_line)
        self.retval, self.stdout, self.stderr = run_command(self.cmd_line)

        self.run_ok = self.retval == 0

        return self.run_ok

    def check(self):
        if not self.run_ok:
            return False

        comp = self.params.get('comp', 'file')
        
        if comp == 'file':
            assert isinstance(self.params['output'], str), "'%s' should be a string" % (self.params['output'],)
            self.check_retval, self.check_stdout, self.check_stderr = run_diff_test(self.tmpfile, self.params['output'])
        elif comp == 'regex':
            assert hasattr(self.params['output'], 'search'), "'%s' should be a compiled regex" % (self.params['output'])
            self.check_retval = run_regex_test(self.stdout, self.params['output'])
            self.check_stdout = ""
            self.check_stderr = ""
        elif comp == "checker":
            assert self.spec.PRODUCES_OUTPUT_FILE, "PRODUCES_OUTPUT_FILE must be True for comp == 'checker'" 
            self.check_retval, self.check_stdout, self.check_stderr = run_checker_test(self.spec.build_checker_cmd_line(self.params, self.tmpfile))
        elif comp == 'pass':
            self.check_retval = 0
            self.check_stdout = ""
            self.check_stderr = ""
        else:
            assert False, "Unrecognized comparison operator: %s" % (comp,)
            self.check_retval, self.check_stdout, self.check_stderr = run_diff_test(self.tmpfile, self.params['output'])

        self.check_pass = self.check_retval == 0

        return self.check_pass

    def cleanup(self):
        if self.tmpfile:
            os.unlink(self.tmpfile)


MULTIPLIERS = {'s': int(1E9), 'ms': int(1E6), 'us': int(1E3), 'ns': 1}

class PerfRun(Run):
    def perf(self):
        """Always returns ns or None"""

        if not (self.run_ok and self.check_pass):
            return None

        if self.spec.PERF_RE is None:
            assert self.spec.PERF_FN
            time_ns = self.spec.PERF_FN(self.stdout, self.stderr)
            return time_ns

        assert self.spec.PERF_RE.flags & re.MULTILINE, "PERF_RE must have MULTILINE set"
        m = self.spec.PERF_RE.search(self.stdout)
        if not m and self.stderr:
            m = self.spec.PERF_RE.search(self.stderr)

        if not m:
            return None

        gd = m.groupdict()

        time_ns = 0
        if "time_ns" in gd:
            # use time_ns only if present
            time_ns = int(gd['time_ns'])
        elif "time_ms" in gd:
            time_ns = int(gd['time_ms']) * MULTIPLIERS['ms']
        elif "time_us" in gd:
            time_ns = int(gd['time_us']) * MULTIPLIERS['us']
        elif "time_s" in gd:
            time_ns = int(gd['time_s']) * MULTIPLIERS['s']
        elif "frac" in gd:
            w, f = int(gd['whole']), int(gd['frac'])

            m = MULTIPLIERS[self.spec.PERF_RE_UNITS]            

            l = len(str(m)) - len(gd['frac'])
            print l
            assert l > 0, l

            time_ns = w * m + f * (10**(l-1))
        else:
            assert False, gd

        return time_ns

def run_test(spec, inp):
    r = Run(spec, inp)
    n = "%s/%s/%s" % (r.bmk_name, spec.BMK_VARIANT, inp)

    if r.run():
        if args.verbose:
            if r.stdout: print >>LOGFILE, r.stdout
            if r.stderr: print >>LOGFILE, r.stderr

        if not r.check():
            print >>LOGFILE, "FAIL:%s: output different: %s" % (n, r.cmd_line_c,)
            #TODO: write output of check?
            return False
        else:
            print >>LOGFILE, "PASS:%s: %s" % (n, r.cmd_line_c,)

            r.cleanup()

            return True
    else:
        print >>LOGFILE, "FAIL:%s: run failed (%d): %s" % (n, r.retval, r.cmd_line_c)
        if r.stdout: print >>LOGFILE, r.stdout
        if r.stderr: print >>LOGFILE, r.stderr
        
        r.cleanup()

        return False

    return True

def run_perf(spec, inp):
    r = PerfRun(spec, inp)
    n = "%s/%s/%s" % (r.bmk_name, spec.BMK_VARIANT, inp)

    if r.run():
        if args.verbose:
            if r.stdout: print >>LOGFILE, r.stdout
            if r.stderr: print >>LOGFILE, r.stderr

        if not r.check():
            print >>LOGFILE, "FAIL:%s: output different: %s" % (n, r.cmd_line_c,)
            #TODO: write output of check?
            return False, None
        else:
            print >>LOGFILE, "PASS:%s: %s" % (n, r.cmd_line_c,)

            r.cleanup()

            return True, r
    else:
        print >>LOGFILE, "FAIL:%s: run failed (%d): %s" % (n, r.retval, r.cmd_line_c)
        if r.stdout: print >>LOGFILE, r.stdout
        if r.stderr: print >>LOGFILE, r.stderr
        
        r.cleanup()

        return False, None

    return True, r

def run_test_on_inputs(spec, inputs):
    for a in inputs:
        v = run_test(spec, a)
        if not v and args.fail_fast:
            return

def run_debug_on_inputs(spec, inputs):
    files = set()
    for a in inputs:
        inp = spec.INPUTS[a]
        if 'input' in inp:
            files.add(inp['input'])
        else:
            print >>sys.stderr, "WARNING: %s does not specify a input file" % (inp['name'])
        if 'output' in inp:
            files.add(inp['output'])
        else:
            print >>sys.stderr, "WARNING: %s does not specify a reference output file" % (inp['name'])         
    
    print "\n".join([f for f in files if isinstance(f, str)])

def run_perf_on_inputs(spec, inputs):
    for a in inputs:
        run = 0
        failed = 0
        
        while run < args.repeat:
            print >>LOGFILE, "PERFDATE", "BEGIN_RUN", datetime.datetime.now().strftime(TIME_FMT)
            v, ro = run_perf(spec, a)
            print >>LOGFILE, "PERFDATE", "END_RUN", datetime.datetime.now().strftime(TIME_FMT)       
            if not v:
                if failed < 3:
                    failed += 1
                    continue
                else:
                    if args.fail_fast:
                        return
                    else:
                        # move to next input
                        break


            run += 1
            p = ro.perf() 
            if p is not None:
                print >>sys.stderr, "PERF", ro.bmk_name, ro.bmk_variant, ro.input, run, p, "'%s'" % (ro.cmd_line_c,)
                print >>LOGFILE, "PERF", ro.bmk_name, ro.bmk_variant, ro.input, run, p, "'%s'" % (ro.cmd_line_c,)
            else:
                print >>sys.stderr, "Unable to extract performance information"

def load_spec(f):
    fp = os.path.join(os.getcwd(), f)
    g = {"__file__": fp}
    execfile(fp, g)
    return g

#bmktest = load_spec("bmktest.py")
import bmktest # for now

parser = argparse.ArgumentParser(description="Run tests")

parser.add_argument("inputs", nargs='?', help="Inputs to run tests on", choices=bmktest.INPUTS.keys())

parser.add_argument("--quick", dest="suite", action="store_const", const="quick", help="Quick inputs")
parser.add_argument("--full", dest="suite", action="store_const", const="full", help="All inputs")
parser.add_argument("-x", dest="exclude", action="append", help="Exclude inputs")
parser.add_argument("-v", dest="verbose", action="store_const", const=True, default=False, help="Verbose logging")
parser.add_argument("-l", dest="log", help="Log to file")
parser.add_argument("--ff", dest="fail_fast", action="store_true", default=False, help="Fail fast")
parser.add_argument("--perf", dest="suite", action="store_const", const="perf", help="Performance inputs")
parser.add_argument("-p", dest="perf", action="store_const", const=True, help="Run performance tests")
parser.add_argument("-r", dest="repeat", metavar="N", type=int, default=3, help="Repeat runs N times for performance")
parser.add_argument("--show-inputs", dest="show_inputs", action="store_true", help="Show all the input files and reference inputs (input/output)")


args = parser.parse_args()

if args.inputs:
    # nargs='*' doesn't work when no input is provided
    inputs = [args.inputs]
elif args.suite == "quick":
    inputs = bmktest.QUICK_TEST_INPUTS
elif args.suite == "full":
    inputs = bmktest.FULL_TEST_INPUTS
elif args.suite == "perf":
    inputs = bmktest.PERF_INPUTS
else:
    if args.show_inputs:
        inputs = bmktest.FULL_TEST_INPUTS
    else:
        inputs = bmktest.DEFAULT_TEST_INPUTS

if args.exclude:
    inputs = [x for x in inputs if x not in args.exclude]

if args.log:
    LOGFILE = open(args.log, "w")
else:
    LOGFILE = sys.stderr

if not args.show_inputs:
    print >>LOGFILE, "SYSTEM", ",".join(os.uname())
    print >>LOGFILE, "DATE", "START", datetime.datetime.now().strftime(TIME_FMT)

if args.perf:
    run_perf_on_inputs(bmktest, inputs)
elif args.show_inputs:
    run_debug_on_inputs(bmktest, inputs)
else:
    run_test_on_inputs(bmktest, inputs)
