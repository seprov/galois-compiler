import gg.ast.walkers
import gg.ast
import gg.passes
import gg.ast.misc.cblocks as cblocks
import itertools

class SymbolChecker(gg.ast.walkers.ASTPreOrderWalkerST):
    
    def generic_node_exit(self, node):
        if isinstance(node, gg.ast.Kernel):
            self.kernel = None
        
    def generic_node_visitor(self, node):
        if isinstance(node, gg.ast.Kernel):
            self.kernel = node

        ok = True
        if isinstance(node, (gg.ast.Invoke, gg.ast.Iterate)):
            ok = self.compiler.check(node.kernel in self.compiler.unit.kernels, "Kernel '%s' not defined" % (node.kernel,), node.__class__.__name__) and ok

        if hasattr(node, 'c_ast'):
            # lookup against correct symbol table
            st = self.symtab.top
            missing = set()

            for symbol in itertools.chain(node.reads, node.writes):
                e = st.lookup(symbol)
                if e:
                    #print symbol, e.ty
                    pass
                else:
                    if symbol not in ('true', 'false') and symbol not in missing:
                        if symbol not in self.compiler.unit.kernels:
                            if hasattr(node, 'parse') and not node.parse:
                                if node.check_gen(self.gen):
                                    self.compiler.log.warning("%s:Symbol '%s' is undefined on no-parse node" % (node.__class__.__name__, symbol,))
                            else:
                                self.compiler.check(False, "Kernel '%s': Symbol '%s' is undefined" % (self.kernel.name, symbol,), node.__class__.__name__)
                                st.dump()
                                missing.add(symbol) 
                                ok = False #?

        return ok

# TODO: check for Invokes on kernels that use WL but Invoke is not in Pipe        

class SemanticCheckerPass(gg.passes.Pass):
    depends = set(['ASTAvail', 'KernelListPass', 
                   'SyntaxCheckerPass', 'SymbolTableBuilderPass', 
                   'RWSetsPass'])

    rdepends = set(['SemCheckedASTAvail'])

    def run(self, compiler, unit, gen, pm):
        w = SymbolChecker()
        w.visit3(compiler, unit.ast, gen)
        if compiler.errors > 0:
            compiler.info("%d error(s) found. Halting." % (compiler.errors,))
            return False

        return True
