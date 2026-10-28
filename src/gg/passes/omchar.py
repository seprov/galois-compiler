import gg.ast.walkers
import gg.ast
import gg.passes
import gg.lib.wl
import gg.lib.graph
import csv
import sys
import os

class OmAnno(gg.ast.ASTNodeAnno):
    clonable = False
    worklist = None


    def __init__(self, worklist = False, loop0_it_type = "NONE", loop1_it_type = "", loop2p_it_type = "", 
                 wlinput = False, trav = False, push = False, kernel=""):

        self.kernel = kernel
        self.worklist = worklist
        self.loop0_it_type = loop0_it_type
        self.loop1_it_type = loop1_it_type
        self.loop2p_it_type = loop2p_it_type

        self.wlinput = wlinput
        self.trav = trav
        self.push = push


class OmAnnotator(gg.ast.walkers.ASTWalker):
    kernel = None
    loops = None

    props = ['kernel', 'worklist', 'loop0_it_type', 'loop1_it_type', 'loop2p_it_type', 'wlinput', 'trav', 'push']

    def _char_iter(self, loop):

        if isinstance(loop, (gg.ast.ForAll, gg.ast.For)):
            it = loop.iterator
        elif isinstance(loop, gg.ast.CFor):
            return "CFOR"
        else:
            assert False, loop
        
        if isinstance(it, gg.lib.wl.WorklistIterator):
            return "WL"
        elif isinstance(it, gg.lib.graph.NodeIterator):
            return "NODE"
        elif isinstance(it, gg.lib.graph.EdgeIterator):
            return "EDGE"
        elif it is None:
            return "NONE"
        else:
            return "UNK(%s)" % (it.__class__.__name__)

    def visit_Kernel(self, node):
        # does not update, which is okay ...
        if node.has_anno("om"):
            return

        if node.host: # TODO: device only kernels?
            return

        assert self.kernel is None
        assert self.loops is None

        self.kernel = node
        self.loops = []
        
        super(OmAnnotator, self).visit_Kernel(node)

        out = {}

        out['kernel'] = node.name
        out['worklist'] = node.contains_wl

        if len(self.loops) >= 1:
            out['loop0_it_type'] = self._char_iter(self.loops[0])
            assert self.loops[0].nesting_level == 1, "%s: %d" % (node.name, self.loops[0].nesting_level,)

        if len(self.loops) > 1:
            if self.loops[1].nesting_level == 2:
                out['loop1_it_type'] = self._char_iter(self.loops[1])
            else:
                out['loop1_it_type'] = ""
                print("IGNORING SECOND LOOP: %s: %d" % (node.name, self.loops[1].nesting_level), file=sys.stderr)

            if len(self.loops) > 2:
                # WARNING: no loop nesting level information available...
                out['loop2p_it_type'] = ";".join([self._char_iter(x) for x in self.loops[2:]])
            else:
                out['loop2p_it_type'] = ""
        else:
            out['loop1_it_type'] = ""
            
        out['wlinput'] = node.outer_forall_is_wl
        out['trav'] = len(self.loops) > 1 and out['loop1_it_type'] == 'EDGE'
        out['push'] = node.writes_wl

        node.anno.om = OmAnno(**out)

        self.kernel = None
        self.loops = None

    def visit_CFor(self, node):        
        self.loops.append(node)
        super(OmAnnotator, self).visit_CFor(node)        

    def visit_For(self, node):
        self.loops.append(node)
        super(OmAnnotator, self).visit_For(node)

    def visit_ForAll(self, node):
        self.loops.append(node)
        super(OmAnnotator, self).visit_ForAll(node)

def qd_binary_variant(d):
    import re

    b2 = os.path.join(d, "bmktest2.py")
    if os.path.exists(b2):
        f = open(b2, "r")
        s = f.read()
        f.close()

        x = re.compile(r"bmk *= *('|\")(?P<bmk>.*)('|\")")
        y = re.compile(r"variant *= *('|\")(?P<variant>.*)('|\")")

        m1 = x.search(s)
        m2 = y.search(s)

        return (m1.group('bmk'), m2.group('variant'))

    return None
        

class OmAnnotatorPass(gg.passes.Pass):
    depends = set(['KernelPropsPass'])
    rdepends = set(['PreOptimizationPass'])

    def __init__(self, outputfile, src):
        self.outputfile = outputfile
        self.src = src

    def run(self, compiler, unit, gen, pm):
        v = OmAnnotator()
        v.visit4(compiler, unit, unit.ast, pm)

        out = []
        for k in unit.kernels:
            kk = unit.kernels[k]
            if kk.has_anno("om"):
                anno = kk.anno.om
                out.append(dict([(p, getattr(anno, p)) for p in OmAnnotator.props]))

        addl = {}
        addl['src'] = self.src
        k = ['src']

        bmkvar = qd_binary_variant(os.path.dirname(self.outputfile))
        if bmkvar is not None:
            addl['bmkvar'] = "%s/%s" % (bmkvar)
            k += ['bmkvar']

        # keep this human readable and editable (mostly)
        f = csv.DictWriter(open(self.outputfile, "w"), k + OmAnnotator.props)
        f.writeheader()
        for o in out:
            o.update(addl)
            f.writerow(o)

        return True
