import toposort # requires py2.7

class PassManager(object):
    def __init__(self):
        self.passes = {}
        self.depends = {}

        self.nodes_generated = False
        self.generation = 0
        self.add_pass([ASTAvail(), SemCheckedASTAvail(),
                       PreOptimizationPass(), PostOptimizationPass(), 
                       PreOutputPass(), 
                       PostOutputPass()])

    def add_pass(self, pl):
        if not isinstance(pl, list):
            pl = [pl]

        for p in pl:
            pn = p.__class__.__name__
            if pn not in self.passes:
                self.passes[pn] = p
                self.depends[pn] = set()

            # TODO: check if p.depends is a valid list of passes?
            self.depends[pn] = p.depends.copy() # for rdepends

    def order_passes(self):
        for pn, p in self.passes.items():
            if hasattr(p, 'rdepends'):
                for rd in p.rdepends:
                    assert rd in self.depends, "Pass '%s' in rdepends of '%s', but not scheduled for execution" % (rd, pn)
                    self.depends[rd].add(pn)

        #TODO: cycle checking
        return toposort.toposort_flatten(self.depends)

    def run_passes(self, compiler, incremental = None, gen = 0):
        op = self.order_passes() # maybe cache this 

        for pn in op:
            if pn == incremental: # TODO, is? (though that requires passes)
                break

            if pn not in self.passes:
                compiler.log.critical("Pass '%s' not found" % (pn,))
                return False

            p = self.passes[pn]

            compiler.log.debug('Running %s[%d] %s ' % (" " * gen, gen, pn,))
            if not p.run(compiler, compiler.unit, gen, self):
                compiler.log.error("Pass failed: %s" % (pn,))
                return False

            if self.nodes_generated:
                self.nodes_generated = False
                self.generation += 1
                if not self.run_passes(compiler, pn, self.generation):
                    if compiler.options.ignore_nested_errors:
                        compiler.errors = 0
                    else:
                        compiler.log.error("Was unable to run incremental passes")
                    #compiler.errors = 0
                        return False

                assert self.nodes_generated == False

        return True

    def set_nodes_generated(self):
        self.nodes_generated = True

class Pass(object):
    depends = set()

    def run(self, compiler, unit, gen, pm):
        return True

class ASTAvail(Pass):
    """AST is available after this pass in unit"""


class SemCheckedASTAvail(Pass):
    """Semantically checked AST is available after this pass in unit"""

    depends = set(['ASTAvail'])


class PreOptimizationPass(Pass):
    """All input transformations are done."""

    depends = set(['SemCheckedASTAvail'])

class PostOptimizationPass(Pass):
    """All optimizations are done."""

    depends = set(['PreOptimizationPass'])

class PreOutputPass(Pass):
    """All backend-independent transformations are done."""

    depends = set(['PostOptimizationPass'])

class PostOutputPass(Pass):
    """All backend transformations are done."""

    depends = set(['PreOutputPass'])
