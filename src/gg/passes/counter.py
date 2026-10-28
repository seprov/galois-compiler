import gg.ast.walkers
from gg.ast import LoopStatements, LoopExitStatements, BlockStatements, Block
from gg.ast.utils import Stack
from gg.ast.misc import cblocks2

class LoopAnnotation(gg.ast.ASTNodeAnno):
    can_exit_early = False 
    countable = False
    clonable = False

class CountAnnotation(gg.ast.ASTNodeAnno):
    unconditional_count = False
    parent_loop = None
    clonable = False

class Counter(gg.ast.walkers.ASTPreOrderWalker):
    def __init__(self):
        super(Counter, self).__init__()
        self.block_stack = Stack()

    def generic_node_exit(self, node):
        if isinstance(node, BlockStatements) and not isinstance(node, Block):
            self.block_stack.pop()

    def generic_node_visitor(self, node):
        if not node.has_anno("count"):
            node.anno.count = CountAnnotation()

        if not self.block_stack.empty():
            t = self.block_stack.top
            if isinstance(t, LoopStatements):
                if t.anno.loop.countable and not t.anno.loop.can_exit_early:
                    # this node will execute for all iterations and has a known count
                    # TODO: what happens when enclosing loop (t) is optimized away and reference to it?
                    if node.check_gen(self.gen):
                        node.anno.count.parent_loop = t
                        node.anno.count.unconditional_count = True
                    
                        if self.compiler.show_cgen(self.gen):
                            self.compiler.log.debug("'%s' in loop '%s' has definite count", node, t)

        if isinstance(node, BlockStatements) and not isinstance(node, Block):
            self.block_stack.push(node)

        return True

class LoopProps(gg.ast.walkers.ASTPreOrderWalker):
    def __init__(self):
        super(LoopProps, self).__init__()
        self.loop_stack = Stack()

    def generic_node_exit(self, node):
        if isinstance(node, LoopStatements):
            self.loop_stack.pop()

    def generic_node_visitor(self, node):
        if isinstance(node, LoopStatements):
            if not node.has_anno("loop"):
                node.anno.loop = LoopAnnotation()

            # TODO: handle uniform 
            node.anno.loop.countable = isinstance(node, gg.ast.ForAll)

            self.loop_stack.push(node)
        else:
            if isinstance(node, LoopExitStatements):
                #TODO: Handle uniform loops

                assert not self.loop_stack.empty()
                self.loop_stack.top.anno.loop.can_exit_early = True

            if hasattr(node, "c_ast") and len(self.loop_stack):
                for p, ast in node.c_ast.items():
                    if not isinstance(ast, list): ast = [ast]

                    for a in ast:
                        st = cblocks2.ContainsControlFlow.get_control_flow(a)
                        if len(st):
                            # not always true, but this is conservative
                            self.loop_stack.top.anno.can_exit_early = True
                            break                

        return True

class CounterPass(gg.passes.Pass):
    depends = set(['KernelPropsPass', 'SemCheckedASTAvail'])
    rdepends = set(['PreOptimizationPass'])

    def run(self, compiler, unit, gen, pm):
        v = LoopProps()
        v.visit2(compiler, unit.ast)

        v = Counter()
        v.visit3(compiler, unit.ast, gen)

        return True
