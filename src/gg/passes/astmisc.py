import gg.passes
from gg.ast import Module, Kernel
import gg.cfg
import gg.ast.walkers
from gg.ast.utils import Stack

class KernelListPass(gg.passes.Pass):
    depends = set(['ASTAvail'])

    def run(self, compiler, unit, gen, pm):
        ast = unit.ast

        if not isinstance(ast, Module):
            compiler.log.error('Top-level AST node is not Module')
            return False

        out = unit.kernels if gen > 0 else {}

        ok = True
        for s in ast.stmts.stmts:
            if isinstance(s, Kernel):
                if s.check_gen(gen):
                    if s.name not in out:
                        out[s.name] = s                    
                    else:
                        compiler.log.error("Kernel '%s' redefined." % (s.name,))
                        ok = False
                else:
                    if s.name not in out:
                        compiler.log.critical("Kernel '%s' not in list of kernels")
                        ok = False
        
        if ok:
            unit.kernels = out

        return ok

class ASTNumber(gg.ast.walkers.ASTPreOrderWalker):
    def generic_node_visitor(self, node):
        if node.check_gen(self.gen):
            #if not node.number is None:
            #    print node.decls
            
            assert node.number is None, "%s/%s" % (node, node.number,)
            node.number = self.unit.node_number + 1
            self.unit.node_number += 1
            
        return True


class ASTNumberingPass(gg.passes.Pass):
    depends = set(['SemCheckedASTAvail'])

    def run(self, compiler, unit, gen, pm):
        v = ASTNumber()
        v.visit4(compiler, unit, unit.ast, gen)
        return True


class CFGBuilderPass(gg.passes.Pass):
    depends = set(['SemCheckedASTAvail'])

    def run(self, compiler, unit, gen, pm):
        unit.cb = gg.cfg.make_cfg(unit.ast)
        
        for c in unit.cb.cfgs:
            gg.cfg.number_nodes(c)
            #TODO: check that all AST nodes were covered
            gg.cfg.check_parents(c)

        return True


class CFG2DOTPass(gg.passes.Pass):
    depends = set(['PostOutputPass'])
    
    def __init__(self, prefix):
        self.prefix = prefix

    def run(self, compiler, unit):
        output_dot_files = []
        for c in unit.cb.cfgs:
            f = "%s-%s.dot" % (self.prefix, c.name)
            of = open(f, "w")
            print("digraph {", file=of)
            gg.cfg.visualize(of, c)
            print("}", file=of)
            of.close()
            output_dot_files.append(f)

        unit.dot_files = output_dot_files
        return True

class RunDOTPass(gg.passes.Pass):
    depends = set(['CFG2DOTPass'])
    
    def run(self, compiler, unit):
        import os, sys

        dot_files = unit.dot_files

        for f in dot_files:
            output = f[:-4] + ".png"
            cmd = "dot -Tpng -o %s %s" % (output, f)
            compiler.log.debug(cmd)
            rv = os.system(cmd)
            if rv != 0:
                compiler.log.error("Running '%s' failed (%d)." % (cmd, rv))
                return False

        return True

class ASTDumperPass(gg.passes.Pass):
    depends = set(['SemCheckedASTAvail', 'PostOutputPass'])
    
    def run(self, compiler, unit, gen, pm):
        import gg.ast.walkers
        w = gg.ast.walkers.Dumper()
        w.visit(unit.ast)
        return True


class STDumperPass(gg.passes.Pass):
    depends = set(['SemCheckedASTAvail', 'SymbolTableBuilderPass', 'PostOutputPass'])
    
    def run(self, compiler, unit, gen, pm):
        m = unit.ast
        m.symtab.dump(True)
        return True


class STWalker(gg.ast.walkers.ASTPreOrderWalkerST):
    last = None

    def __init__(self):
        super(STWalker, self).__init__()
        self.last = Stack()

    def generic_node_exit(self, node):
        self.last.pop()

    def generic_node_visitor(self, node):
        if len(self.last):
            if self.last.top != self.symtab.top:
                self.symtab.top.dump(False)
        else:
            self.symtab.top.dump(False)

        self.last.push(self.symtab.top)
        return True

class STWalkerPass(gg.passes.Pass):
    depends = set(['SemCheckedASTAvail', 'SymbolTableBuilderPass', 'PostOutputPass'])
    
    def run(self, compiler, unit, gen, pm):
        v = STWalker()
        v.visit2(compiler, unit.ast)
        return True
