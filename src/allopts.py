#!/usr/bin/env python
# generate all possible compiler combinations 

import sys
import itertools
from itertools import chain, combinations
from collections import OrderedDict, namedtuple

allcombos = namedtuple('allcombos', ['name', 'combo', 'cmdline', 'index'])

# TODO: generate this by introspecting ggc's argument parser?
names_to_options = OrderedDict([('coop', '--opt coop'),
                                ('parcomb', '--opt parcomb'),
                                ('oitergb', '--opt oitergb'),
                                ('backoff', '--opt backoff'),
                                ('oiter', '--opt oiter'),
                                ('unroll_pipes', '--unroll pipes'),
                                ('np', OrderedDict([('np', '--opt np'),
                                                    ('_opts_', OrderedDict([('tb', '--nps tb'),
                                                                            ('wp', '--nps wp'),
                                                                            #'fg', '--nps fg',
                                                                            ('fg', OrderedDict([('fg', '--nps fg'),
                                                                                                ('_mustdescend_', False),
                                                                                                ('_opts_', OrderedDict([('npf8', '--npf 8')])),
                                                                                            ]),
                                                                         )])),
                                                   ('_mustdescend_', True)]
                                               )),
                                ])

def powerset(iterable):
    "powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(len(s)+1))

def combos(opts, name = '', depth = 0):
    #print "\t" * depth, "entering", name, opts

    descendents = []
    md = False

    if isinstance(opts, dict):
        if '_opts_' in opts:
            children = opts['_opts_']
            k = [kk for kk in list(opts['_opts_'].keys()) if kk not in set(['_opts_', '_mustdescend_'])]
        else:
            assert depth == 0
            children = opts

        k = [kk for kk in list(children.keys()) if kk not in set(['_opts_', '_mustdescend_'])]
        md = '_mustdescend_' in opts and opts['_mustdescend_']

        for opt in k:
            #for d in combos(children[opt], opt, depth + 1):
            descendents.append(combos(children[opt], opt, depth + 1))
        
    out = [None]
    if not md and name != '':
        #print "\t" * depth, "md", name
        out.append(name)
        
    if depth == 0:
        name = None

    for j in itertools.product([name], *descendents):
        x = [jj for jj in j if jj is not None]
        #if len(x) <= 1: continue   
        if depth > 0 and len(x) <= 1: continue   
        if depth == 0 and len(x) < 1: continue   

        out.append(x)

    return out

def expand_command_line(treelist, n2o):
    out = []

    if treelist is not None:
        for x in treelist:
            if isinstance(x, list):
                out.extend(expand_command_line(x, n2o))
            else:
                assert x in n2o, "Missing '%s' in %s" % (x, n2o)

                if isinstance(n2o[x], str):
                    out.append(n2o[x])
                else:
                    assert '_opts_' in n2o[x]
                    out.append(n2o[x][x])
                    n2o = n2o[x]['_opts_']

    return out

def name_command_line(treelist, n2o):
    out = []

    if treelist is not None:
        for x in treelist:
            if isinstance(x, list):
                out.extend(name_command_line(x, n2o))
            else:
                assert x in n2o, "Missing '%s' in %s" % (x, n2o)

                if isinstance(n2o[x], str):
                    out.append(x)
                else:
                    assert '_opts_' in n2o[x]
                    out.append(x)
                    n2o = n2o[x]['_opts_']

    return out

def print_tree(treelist, depth = 0):
    for y in treelist:
        if isinstance(y, list):
            print_tree(y, depth + 1)
        else:
            print("\t" * depth, y)

def get_all_combos():
    count = 0
    for elem in combos(names_to_options):
        cmdline = expand_command_line(elem, names_to_options)
        name = name_command_line(elem, names_to_options)
        combo = elem
        
        yield allcombos(name=name, combo=combo, cmdline = cmdline, index=count)
        count += 1

if __name__ == "__main__":
    import argparse
    
    p = argparse.ArgumentParser("Generate all options")
    p.add_argument("template", help="Command line template to generate")

    args = p.parse_args()

    for c in get_all_combos():
        sname = "+".join(c.name)
        if len(c.name) == 0:
            assert len(c.cmdline) == 0
            cmdline = ["--dis-opt all"]
        
        cmdline = " ".join(c.cmdline)

        print(args.template.format(name = sname, cmdline = cmdline))
