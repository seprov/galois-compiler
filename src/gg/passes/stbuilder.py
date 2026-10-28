import gg.ast.walkers
import gg.ast
import gg.passes
import gg.ast.utils
from gg.symtab import *

# TODO: use Block as an organizing construct, especially for If, etc.

BlockStatements = gg.ast.BlockStatements

# Symbols are 
#
#  Block statement {
#    optional-symbols
#    {
#      block body symbols
#    }
#
#  If Block == Kernel, optional-symbols == args, for example.
#
# Compiling to C, we would have (for block statements *other* than Kernel)
#
#   {
#      optional-symbols
#
#      for(optional-symbols-used) { //e.g.
#         block-body-symbols
#         ... code ...
#      }
#   }
#

class SymbolTableBuilder(gg.ast.walkers.ASTPreOrderWalker):
    def __init__(self):
        self.symtab = gg.ast.utils.Stack()        

    def generic_node_exit(self, node):
        if isinstance(node, BlockStatements):
            self.symtab.pop()

    def generic_block_visit(self, blk):
        if isinstance(blk, gg.ast.Block):
            self.visit(blk)
        else:
            # backward compatibility
            for s in blk:
                self.visit(s)

    def generic_node_visitor(self, node):
        if isinstance(node, BlockStatements):
            if not node.check_gen(self.gen):
                self.symtab.push(node.symtab)
            else:                
                if len(self.symtab):
                    self.symtab.push(SymbolTable(node, parent=self.symtab.top))
                else:
                    st = SymbolTable(node)

                    # add a separate symtab for builtins?
                    st.add('true', '#const', is_builtin = True)
                    st.add('false', '#const', is_builtin = True)

                    # TODO: add C symbols
                    st.add('stderr', 'FILE *', is_builtin = True)
                    st.add('stdin', 'FILE *', is_builtin = True)
                    st.add('stdout', 'FILE *', is_builtin = True)

                    # TODO: these are CUDA symbols
                    st.add('TB_SIZE', '#const', is_builtin = True, cval=256)
                    st.add('__kernel_tb_size', '#const', is_builtin = True)
                    st.add('MAX_TB_SIZE', '#const', is_builtin = True)
                    st.add('tid', '#const', is_builtin = True)
                    st.add('nthreads', '#const', is_builtin = True)
                    st.add('threadIdx', '#const', is_builtin = True)

                    self.symtab.push(st)                

                node.symtab = self.symtab.top

        if hasattr(node, "symbols") and node.check_gen(self.gen):  # symbols in current scope
            syms = node.symbols()
            node.declares = set()
            st = self.symtab.top

            for name, ty, ot in syms:
                # TODO: some checking for duplicates
                st.add(name, ty, **ot)
                node.declares.add(name)

        return True 

class SymbolTableChecker(gg.ast.walkers.ASTPreOrderWalkerST):
    def generic_node_visitor(self, node):
        if isinstance(node, BlockStatements):
            # all block nodes must have .symtab
            self.compiler.check_internal(hasattr(node, 'symtab'), "(Internal) Block statement node does not have .symtab", node)

            # only the topmost symtab can have a parent equal to None
            self.compiler.check_internal(not node.symtab.parent is None or len(self.symtab) == 1, "(Internal) Symtab hierarchy broken, parent is None", node)

            # make sure this node's symtab's parent is the previous symtab in the stack
            self.compiler.check_internal(not node.symtab.parent is not None or node.symtab.parent is self.symtab.stk[-2], "(Internal) Symtab hierarchy broken", node)

        return True

class SymbolTableBuilderPass(gg.passes.Pass):
    depends = set(['ASTAvail', 'SyntaxCheckerPass'])
    rdepends = set(['SemCheckedASTAvail'])

    def run(self, compiler, unit, gen, pm):
        w = SymbolTableBuilder()
        w.visit3(compiler, unit.ast, gen)

        return True

class SymbolTableCheckerPass(gg.passes.Pass):
    depends = set(['PostOptimizationPass'])
    rdepends = set(['PreOutputPass'])

    def run(self, compiler, unit, gen, pm):
        v = SymbolTableChecker()
        v.visit3(compiler, unit.ast, gen)

        return compiler.errors == 0
