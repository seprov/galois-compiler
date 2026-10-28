import gg.ast.modifier, gg.ast.walkers
from gg.ast.anno import Uniform
import gg.ast
import gg.passes
from gg.ast.utils import *
import gg.cfg
import gg.dfa.dom, gg.dfa.focal, gg.dfa.cdep
import sys
import logging

logger = logging.getLogger(__name__)

class Uniformizer(gg.ast.modifier.ASTModifier):
    def visit_Kernel(self, node):
        self.need_uniform = Stack()
        self.need_uniform.push(False)
        return super(Uniformizer, self).visit_Kernel(node)
        self.need_uniform.pop()

    def visit_ForAll(self, node):
        self.need_uniform.push(False)
        node = super(Uniformizer, self).visit_ForAll(node)
        u = self.need_uniform.pop()
        if u:
            #TODO: incremental update of uniform, esp as Exclusive can be added later, so gen is not foolproof
            self.need_uniform.top = True
            self.compiler.info("Uniformizer: Converting ForAll(%s) to Uniform [contains GlobalBarrierSync or Exclusive or both]" % node.ndxvar.var_name)
            return Uniform(node)
        else:
            return node

    def visit_Exclusive(self, node):
        self.need_uniform.top = True
        return super(Uniformizer, self).visit_Exclusive(node)

    def visit_MethodInvocation(self, node):

        if node.obj_type == "GlobalBarrier" and node.method == "sync":
            self.need_uniform.top = True

        return super(Uniformizer, self).visit_MethodInvocation(node)

class UniformityChecker2(object):
    def __init__(self, compiler, unit):
        self.compiler = compiler
        self.unit = unit

    def strify(self, astnode):
        if isinstance(astnode, gg.ast.CBlock):
            if hasattr(astnode, 'decls'):
                return "\\n".join(["%s %s" % (v[0], v[1]) for v in astnode.decls])
            else:
                return "\\n".join([str(s) for s in astnode.stmts])
        elif isinstance(astnode, gg.ast.Block):
            return "Block"

        return str(astnode)

    def visnode(self, node):
        out = {'label': '"%s"' % self.strify(node.astnode)}

        #if node.astnode.has_anno("uniform") and node.astnode.anno.uniform.uniform:
        #    out['style'] = 'filled'
        #    out['fillcolor'] = 'yellow'

        dom_exit = self.dfa.info(self.dfa.cfg.exit_node)
        if node.node_id in dom_exit.values:
            out['style'] = 'filled'
            out['fillcolor'] = 'yellow'
            

        return out

    def visedge(self, nodea, nodeb):
        if nodea.node_id > nodeb.node_id:
            return {'color': 'red'}

        return {}

    def _test(self):
        for c in self.unit.cb.cfgs:
            # must be nodes on which control dependent

            # a = set()
            f = c.name + ".dot"
            print(f)
            of = open(f, "w")
            print("digraph {", file=of)
            gg.cfg.visualize(of, c)
            print("}", file=of)
            of.close()

            y = gg.dfa.dom.PostDominators(c)
            y.analyze()
            y.dump(sys.stdout)
            print(y.frontier())
            self.dfa = y
            
    def dump_cfg(self, c):
        f = c.name + ".dot"
        print(f)
        of = open(f, "w")
        print("digraph {", file=of)
        gg.cfg.visualize(of, c)
        print("}", file=of)
        of.close()

    def transitive_cdep(self, allcdep):
        changed = True
        while changed:
            changed = False
            for n in allcdep:
                olddep = allcdep[n]
                x = set(olddep)
                for p in olddep:
                    x = x.union(allcdep[p])

                if x != olddep:
                    allcdep[n] = x
                    changed = True
            
    def check_uniformity_2(self):
        for c in self.unit.cb.cfgs:
            # must be nodes on which control dependent
            y = gg.dfa.dom.PostDominators(c)
            y.analyze()
            #y.dump(sys.stdout)
            allcdep = y.frontier()
            #print allcdep
            self.transitive_cdep(allcdep)

            nd = y.all_nodes_dict()
            for n in nd.values():
                node = n.astnode
                if not (node.has_anno("uniform") and  node.anno.uniform.place_uniform):
                    continue

                cdep = allcdep[n.node_id]
                #print "checking node for uniform placement", n.node_id, node, cdep
                for p in cdep:
                    pp = nd[p]
                    pn = pp.astnode

                    # TODO: verify this list
                    if not isinstance(pn, (gg.ast.For, gg.ast.While, gg.ast.DoWhile, gg.ast.Exclusive, gg.ast.Atomic, gg.ast.If, gg.ast.CFor)):
                        continue

                    if self.compiler.check_internal(pn.has_anno("uniform"), "2: (Internal) Path node %s does not contain uniform attribute" % (pn,), node, _warn = True):
                        # every node in path must be uniform
                        self.compiler.check_internal(pn.anno.uniform.uniform == True, "2: (Internal) Path node %s cannot be determined to be uniform" % (pn,), node, _warn = True)

                    # once we have break/return integrated we may not have to check this separately? 
                    #if pn.has_anno("loop"):
                        # TODO: this is not true when if(UniformCondition) break; for example in a uniform loop.
                    #    if not self.compiler.check_internal(pn.anno.loop.can_exit_early == False, "2: (Internal) Loop node %s can exit early (this may cause it to be not uniform!)" % (pn,), node, _warn = True):
                    #        brk = True


# TODO: Correctly handle breaks, continues, RFPFs and other random
# control flow, right now, this is incorrect.

class UniformityChecker(gg.ast.walkers.ASTPreOrderWalker):
    def __init__(self):
        self.path_stack = Stack()

    def generic_node_exit(self, node):
        if not self.path_stack.empty() and self.path_stack.top is node:
            self.path_stack.pop()

    def generic_node_visitor(self, node):
        if isinstance(node, gg.ast.Kernel):
            assert len(self.path_stack) == 0

            if node.host:                
                return False
            
        if isinstance(node, (gg.ast.Kernel, gg.ast.For, gg.ast.While, gg.ast.DoWhile, gg.ast.Exclusive, gg.ast.Atomic, gg.ast.If, gg.ast.CFor)):
            self.path_stack.push(node)     
            
        if node.has_anno("uniform"):
            if node.anno.uniform.place_uniform:
                for pn in self.path_stack.stk:
                    if isinstance(pn, gg.ast.Kernel): continue # assumed implicitly parallel
                    
                    # every node in path must have a uniform attribute
                    if self.compiler.check_internal(pn.has_anno("uniform"), "(Internal) Path node %s does not contain uniform attribute" % (pn,), node, _warn = True):
                        # every node in path must be uniform
                        self.compiler.check_internal(pn.anno.uniform.uniform == True, "(Internal) Path node %s cannot be determined to be uniform" % (pn,), node, _warn = True)

                    if pn.has_anno("loop"):
                        # TODO: this is not true when if(UniformCondition) break; for example in a uniform loop.
                        self.compiler.check_internal(pn.anno.loop.can_exit_early == False, "(Internal) Loop node %s can exit early (this may cause it to be not uniform!)" % (pn,), node, _warn = True)

        return True

class ApplyUniformConditional(gg.ast.modifier.ASTModifier):
    def __init__(self):
        self.path_stack = Stack()

    def visit(self, node):
        eliminate = False
        if node.has_anno("uniform_cond"):
            uniform = self.path_stack.top.has_anno("uniform") and self.path_stack.top.anno.uniform.uniform
            eliminate = (uniform != node.anno.uniform_cond.uniform_only)

            if node.anno.uniform_cond._only_if_np and eliminate:
                eliminate = self.compiler.options.np
                
            if eliminate:
                self.compiler.log.info("Eliminating %s, Uniform: %s, Uniform_Only: %s" % (node, uniform, 
                                                                                          node.anno.uniform_cond.uniform_only))


        pushed = False
        if isinstance(node, (gg.ast.Kernel, gg.ast.For, gg.ast.While, gg.ast.DoWhile, gg.ast.Exclusive, gg.ast.Atomic, gg.ast.If, gg.ast.CFor)):
            pushed = True
            self.path_stack.push(node)

        # not necessary if eliminating ...
        x = super(ApplyUniformConditional, self).visit(node)

        if pushed:
            self.path_stack.pop()

        if eliminate:
            return []
        else:
            return x
        
class UniformizerPass(gg.passes.Pass):
    depends = set(['SemCheckedASTAvail'])

    def run(self, compiler, unit, gen, pm):
        v = Uniformizer()
        v.visit3(compiler, unit, unit.ast, gen)

        return True

class Test(object):
    def __init__(self, compiler, unit):
        self.compiler = compiler
        self.unit = unit

    def strify(self, astnode):
        if isinstance(astnode, gg.ast.CBlock):
            if hasattr(astnode, 'decls'):
                return "\\n".join(["%s %s" % (v[0], v[1]) for v in astnode.decls])
            else:
                return "\\n".join([str(s) for s in astnode.stmts])
        elif isinstance(astnode, gg.ast.Block):
            return "Block"

        return str(astnode)

    def visnode(self, node):
        d = self._dom.info(node).values
        f = self._dfa.info(node).values
        cm = []
        for x in f:
            if x in d:
                cm.append("%s*" % (x,))
            else:
                cm.append("%s" % (x,))

        out = {'label': '"%s: %s %s"' % (node.node_id, self.strify(node.astnode), ",".join(cm))}

        if node.node_id in self.fc.values:
        #if node.astnode.has_anno("uniform") and node.astnode.anno.uniform.uniform:
            out['style'] = 'filled'
            out['fillcolor'] = 'yellow'

        if node.astnode.has_anno("uniform") and node.astnode.anno.uniform.uniform:
        #if node.node_id in self.fc.values:
            if 'style' in out:
                out['style'] = '"rounded,' + out['style'] + '"'
            else:
                out['style'] = 'rounded'

        out['shape'] = 'rect'
        return out

    def visedge(self, nodea, nodeb):
        out = {}

        if nodeb in nodea.non_code_edges:
            out['style'] = 'dashed'
        #else:
        #    self.unit.cb.add_at_edge(nodea, nodeb, gg.ast.CBlock('printf("%d -> %d\\n")' % (nodea.node_id, nodeb.node_id)))

        # if dst node is a focal point
        if nodeb.node_id in self.fc.values:
            if nodea.node_id in self._dom.info(nodeb).values:
                if nodeb not in nodea.non_code_edges:
                    out['penwidth'] = '3'
                    self.unit.cb.add_at_edge(nodea, nodeb, gg.ast.CBlock('// FP: "%d -> %d' % (nodea.node_id, nodeb.node_id), 
                                                                         parse=False))

        if nodea.node_id > nodeb.node_id:
            out['color'] = 'red'

        return out

    def _test(self):
        for c in self.unit.cb.cfgs:
            # must be nodes on which control dependent
            x = gg.dfa.dom.Dominators(c)
            x.analyze()
            logger.debug("Immediate Dom %s" % (x.immediate(),))

            z = gg.dfa.dom.PostDominators(c)
            z.analyze()
            ipdom = z.immediate()
            
            a = gg.dfa.focal.FocalPointsCDep(c)
            #a._debug = 1
            a.analyze()
            fc2 = a.get_focal_points()
            a.analyze2(strict=False)
            fc3 = a.get_focal_points()

            assert fc2.values == fc3.values, "%s %s" % (fc2.values, fc3.values)

            a.dump_cdg(open("cdep_" + c.name + ".dot", "w"))

            y = gg.dfa.focal.FocalPoints(c)
            y.analyze(z)
            fc = y.get_focal_points()

            logger.debug("FOCAL POINTS %s %s %s" % (fc.values, fc2.values, fc.values == fc2.values,))

            if True:
                fcv = a.verify(fc.values)
                fc2v = a.verify(fc2.values)

                if len(fcv) != 0:                    
                    logger.critical("Focal points failed verification %s" % (fcv,))

                if len(fc2v) != 0:
                    logger.critical("Focal points 2 failed verification %s" % (fc2v,))
                    #assert len(fc2v) == 0, fc2v

                if fc.values != fc2.values:
                    logger.debug("\t** In fc %s " % (fc.values - fc2.values,))
                    logger.debug("\t** In fc2 %s" % (fc2.values - fc.values,))

            self._dfa = y
            self._dom = x
            self.fc = fc2
            self._cfg = c

            # a = set()
            f = c.name + ".dot"
            print(f)
            of = open(f, "w")
            print("digraph {", file=of)
            gg.cfg.custom_visualize(of, c, self.visnode, self.visedge)
            print("}", file=of)
            of.close()

    def dump_cfg(self, c):
        f = c.name + ".dot"
        print(f)
        of = open(f, "w")
        print("digraph {", file=of)
        gg.cfg.visualize(of, c)
        print("}", file=of)
        of.close()


class UniformityCheckerPass(gg.passes.Pass):
    depends = set(['PostOptimizationPass'])
    rdepends = set(['PreOutputPass'])

    def run(self, compiler, unit, gen, pm):
        x = Test(compiler, unit)
        x._test()
        
        x = UniformityChecker2(compiler, unit)
        x.check_uniformity_2()

        v = UniformityChecker()
        v.visit3(compiler, unit.ast, gen)

        v = ApplyUniformConditional()
        v.visit3(compiler, unit, unit.ast, gen)

        return compiler.errors == 0
