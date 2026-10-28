# performance numbers processing framework
# author: sreepathi pai
# copyright: UT, Austin

import logging
import csv
from asq.initiators import query
import sys

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

RUN = "run"
SUITE = "suite"
BMK = "bmk"
BMK_VARIANT = "bmkvar"
NORM_BMK_VARIANT = "norm_" + BMK_VARIANT
INPUT_FILE = "input_file"
INPUT="input"
TIME_MS="time_ms"
TIME_NS="time_ns"
EXP_ID="exp_id"
AVG_TIME_NS = "avg_time_ns"
AVG_TIME_NS_NORM = "avg_time_ns_norm"
RUNS="runs"
SUM_TIME = "_sum_time"
CMDLINE = "cmd_line"            

ORDERING = [EXP_ID, SUITE, BMK, BMK_VARIANT, INPUT, TIME_NS, AVG_TIME_NS, AVG_TIME_NS_NORM, RUN, RUNS, INPUT_FILE, TIME_MS, CMDLINE]

ORDERING = dict([(k, i) for i, k in enumerate(ORDERING)])

class Table(object):
    rows = None

    def __init__(self, rows):
        assert isinstance(rows, list)
        self.rows = rows

    def add_time_ns(self):
        for l in self.rows:
            if TIME_NS in l:
                l[TIME_NS] = int(l[TIME_NS])
                continue

            if TIME_MS in l:
                w, f = split_decimal_str(l[TIME_MS])
                l[TIME_NS] = w * 10**6 + f

        return self

    def add_columns(self, kvpairs):
        for rid, r in enumerate(self.rows):
            for (k, v) in kvpairs.items():
                if k in r:
                    log.debug("Column '%s' already in row %d, not adding" % (k, rid))
                    continue

                if callable(v):
                    r[k] = v(r)
                else:
                    r[k] = v

        return self

    def cvt_std_types(self):
        for r in self.rows:
            if RUN in r:
                r[RUN] = int(r[RUN])

            if TIME_NS in r:
                r[TIME_NS] = int(r[TIME_NS])
                
        return self
        
    def print_list(self):
        header = list(self.rows[0].keys())
        print(" ".join(header))
        for r in self.rows:
            for k in header:
                print(r[k], end=' ')
            print()

    def write_csv(self, outputfile, user_order = None):
        def pos(k):
            sp = k.find("/")
            if sp != -1:
                k = k[sp+1:]

            if k in ORDERING:
                return ORDERING[k]

            if k in user_order_dict:
                return len(ORDERING) + user_order_dict[k]
            
            if k in unsorted_dict:
                return len(ORDERING) + len(user_order_dict) + unsorted_dict[k]

            log.warning("'%s' unsorted" % (k,))
            return len(ORDERING) + len(user_order_dict) + len(unsorted_dict) + 1
            assert False, k
            
        user_order_dict = {} if user_order is None else [(u, i) for i, u in enumerate(user_order)]

        headers = sorted(self.rows[0].keys())
        unsorted_dict = [(k, i) for i, k in enumerate(headers) if k not in ORDERING and k not in user_order_dict]

        headers.sort(key = pos)

        if outputfile == "-":
            of = sys.stdout
        else:
            of = open(outputfile, "w")

        c = csv.DictWriter(of, headers)

        c.writeheader()

        for r in self.rows:
            c.writerow(r)

    @staticmethod
    def read_csv(inputfile):
        if inputfile == "-":
            of = sys.stdin
        else:
            of = open(inputfile, "r")

        c = csv.DictReader(of)
        out = []
        for r in c:
            out.append(r)

        x = Table(out)
        x.cvt_std_types()
        return x

    def combine(self, t): # really append
        def combiner(tt, mk):
            out = []
            mkd = dict([(k, "") for k in mk])

            for r in tt:
                x = r.copy()
                x.update(mkd)
                out.append(x)

            return out
                
        if self.rows:
            k1 = set(self.rows[0].keys()) 
        else:
            k1 = set()

        if t.rows:
            k2 = set(t.rows[0].keys())
        else:
            k2 = set()

        k1m = k2.difference(k1)
        k2m = k1.difference(k2)

        x1 = combiner(self.rows, k1m)
        x2 = combiner(t.rows, k2m)
        
        return Table(x1 + x2)
        
    def merge(self, t, tprefix): # really an outer join
        merge_keys = (BMK, BMK_VARIANT, INPUT)
        select = (AVG_TIME_NS, AVG_TIME_NS_NORM, NORM_BMK_VARIANT)

        def sel(r): # support prefix?
            out = dict([(k, r[k]) for k in merge_keys])
            out.update(dict([(k, r[k]) for k in select]))
            return out

        def key(r):
            if r is None: return None
            return tuple([r[k] for k in merge_keys])
        
        def safe_next(i):
            try:
                x = next(i)
                return x
            except StopIteration:
                return None

        notfirst = any(["/" in k for k in list(self.rows[0].keys())])

        if notfirst:
            t1 = query(self.rows).order_by(key)
            t2 = query(t.rows).order_by(key)
        else:
            t1 = query(self.rows).select(sel).order_by(key)
            t2 = query(t.rows).select(sel).order_by(key)
        
        i1 = iter(t1)
        i2 = iter(t2)

        r1 = next(i1)
        r2 = next(i2)

        out = []
        while True:
            if r1 is None and r2 is None:
                break # we're done
            
            if key(r1) == key(r2):
                out.append((r1, r2))
                r1 = safe_next(i1)
                r2 = safe_next(i2)
            elif r2 is None or key(r1) < key(r2):
                o = dict([(k, r1[k]) for k in merge_keys])
                out.append((r1, o))
                r1 = safe_next(i1)
            elif r1 is None or key(r1) > key(r2):
                o = dict([(k, r2[k]) for k in merge_keys])
                out.append((o, r2))
                r2 = safe_next(i2)

        out2 = []
        for r in out:
            r1, r2 = r
            out2.append(r1)
            for k in select:
                if k in r2:
                    r1[tprefix + "/" + k] = r2[k]
                else:
                    r1[tprefix + "/" + k] = ""

        return Table(out2)

    def update(self, t):
        n = set(query(t.rows).select(lambda x: (x[BMK], x[BMK_VARIANT], x[INPUT])).distinct()) 

        print(n, file=sys.stderr)
        print(self.rows, file=sys.stderr)

        # remove matching runs in self
        o = query(self.rows).where(lambda x: (x[BMK], x[BMK_VARIANT], x[INPUT]) not in n)

        t = Table(o.to_list()).combine(t)

        return t
        

def read_table_file(f, headers=None, compress=False):
    if compress:
        assert False, "compress not yet implemented"

    of = open(f, "r")

    out = []
    ol = 0
    for i, l in enumerate(of):
        ls = l.strip().split(" ") # TODO: handle tabs?

        if not len(out) and headers is None:
            headers = ls
            continue
        
        if len(out) and len(ls) != ol:
            log.warning("%d: number of columns %d differs from first row %d", i, len(ls, l))
            
        if not len(out):
            ol = len(ls)
                        
        if headers:
            assert len(ls) == len(headers), "%d: has fewer columns (%d) than headers" % (i, len(ls))
            o = dict([(k, v) for k, v in zip(headers, ls)])
            out.append(o)
        else:
            out.append(ls)

    return Table(out)

class Analysis(object):
    def __init__(self, table):
        self.table = table

    def suite_perf(self):
        def rs(key, group):
            exp_id, suite, bmk, bmk_variant, inp = key

            sum_time = sum([g[TIME_NS] for g in group])
            avg_time = float(sum_time) / len(group)
            # TODO: stddev

            return {EXP_ID: exp_id, SUITE: suite, BMK: bmk, 
                    BMK_VARIANT: bmk_variant, INPUT: inp, 
                    AVG_TIME_NS: avg_time, 
                    SUM_TIME: sum_time, 
                    RUNS: len(group)}
            
        return Table(query(self.table.rows).group_by(lambda x: (x[EXP_ID], x[SUITE], x[BMK], x[BMK_VARIANT], x[INPUT]), result_selector = rs).to_list())

    def fastest_variant(self):
        x = self.suite_perf()

        return Table(query(x.rows).group_by(lambda x: (x[BMK], x[INPUT]), result_selector = lambda k, g: min(g, key=lambda i: i[AVG_TIME_NS])).to_list())

    def normalize_suite_perf(self, to):
        def norm(inner, outer):
            inner[AVG_TIME_NS + "_norm"] = inner[AVG_TIME_NS] / outer[AVG_TIME_NS]
            inner["norm_" + BMK_VARIANT] = outer[BMK_VARIANT] 
            inner["norm_" + AVG_TIME_NS] = outer[AVG_TIME_NS] 

            return inner

        def var_per_inp(k, g):
            out = {}
            for v, i in g:
                if i not in out: 
                    out[i] = set([v])
                else:
                    out[i].add(v)

            return (k, out)

        x = self.suite_perf()

        not_in_to = query(x.rows).difference(to.rows, lambda y: (y[BMK], y[INPUT]))
        not_in_me = query(to.rows).difference(x.rows, lambda y: (y[BMK], y[INPUT]))
        # does every variant have a full complement of inputs?
        bmk_inputs_var = query(x.rows).group_by(lambda x: x[BMK], lambda x: (x[BMK_VARIANT], x[INPUT]), var_per_inp).to_list()
        bmk_vars = dict(query(x.rows).distinct(lambda x: (x[BMK], x[BMK_VARIANT])).group_by(lambda x: x[BMK], lambda x: x[BMK_VARIANT], lambda k, v: (k, set(v))))

        for bmk, inp_var in bmk_inputs_var:
            bmk_var = bmk_vars[bmk]
            for inp, var in list(inp_var.items()):
                if var != bmk_var:
                    missing = bmk_var.difference(var)
                    for m in missing:
                        log.warning("%s/%s was not run on input %s" % (bmk, m, inp))

        for i in not_in_to:
            log.warning("%s/%s not in baseline" % (i[BMK], i[INPUT]))
        
        for i in not_in_me:
            log.warning("%s/%s in baseline, but not in suite" % (i[BMK], i[INPUT]))
                
        return Table(query(x.rows).join(to.rows, lambda y: (y[BMK], y[INPUT]), lambda y: (y[BMK], y[INPUT]), result_selector = norm).order_by(lambda y: (y[SUITE], y[BMK], y[BMK_VARIANT], y[INPUT])).to_list())

    def normalize_suite_perf_to_prev(self, to):
        def norm(inner, outer):
            inner[AVG_TIME_NS + "_norm"] = inner[AVG_TIME_NS] / outer[AVG_TIME_NS]
            inner["norm_" + BMK_VARIANT] = outer[BMK_VARIANT] 
            inner["norm_" + AVG_TIME_NS] = outer[AVG_TIME_NS] 

            return inner

        x = self.suite_perf()

        not_in_to = query(x.rows).difference(to.rows, lambda y: (y[BMK], y[BMK_VARIANT], y[INPUT]))
        not_in_me = query(to.rows).difference(x.rows, lambda y: (y[BMK], y[BMK_VARIANT], y[INPUT]))

        for i in not_in_to:
            log.warning("%s/%s/%s not in baseline" % (i[BMK], i[BMK_VARIANT], i[INPUT]))
        
        for i in not_in_me:
            log.warning("%s/%s/%s in baseline, but not in suite" % (i[BMK], i[BMK_VARIANT], i[INPUT]))
                
        return Table(query(x.rows).join(to.rows, lambda y: (y[BMK], y[BMK_VARIANT], y[INPUT]), lambda y: (y[BMK], y[BMK_VARIANT], y[INPUT]), result_selector = norm).order_by(lambda y: (y[SUITE], y[BMK], y[BMK_VARIANT], y[INPUT])).to_list())


#TODO: equivalent to read table file for CSV files

def split_decimal_str(n):
    p = n.find(".")
    if p != -1:
        whole = int(n[:p])
        frac = int(n[p+1:])
    else:
        whole = int(n)

    return (whole, frac)
    
        
        
