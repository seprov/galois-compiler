from gg.ast import *
from gg.ast.utils import Stack
from gg.ast.ctxmgr import *

class ASTWalker(object):
    def __init__(self):
        pass

    def visit_Module(self, node):
        self.visit(node.stmts)

    def visit_Kernel(self, node):
        self.visit(node.stmts)

    def visit_Pipe(self, node):
        self.visit(node.stmts)

    def visit_While(self, node):
        self.visit(node.stmts)

    def visit_DoWhile(self, node):
        self.visit(node.stmts)

    def visit_Assign(self, node):
        self.visit(node.rhs)

    def visit_ForAll(self, node):
        self.visit(node.stmts)

    def visit_Names(self, node):
        pass

    def visit_CFor(self, node):
        self.visit(node.stmts)

    def visit_For(self, node):
        self.visit(node.stmts)

    def visit_If(self, node):
        self.visit(node.true_stmts)
        self.visit(node.false_stmts)

    def visit_Atomic(self, node):
        self.visit(node.stmts)
        self.visit(node.fail_stmts)

    def visit_Exclusive(self, node):
        self.visit(node.stmts)
        self.visit(node.fail_stmts)

    def visit_Retry(self, node):
        pass

    def visit_CBlock(self, node):
        pass

    def visit_CExpr(self, node):
        pass

    def visit_Block(self, node):
        assert isinstance(node.stmts, list), node.stmts
        for s in node.stmts:
            self.visit(s)

    def visit_Invoke(self, node):
        pass

    def visit_Iterate(self, node):
        self.visit(node.stmts)

    def visit_MethodInvocation(self, node):
        pass

    def visit_ReturnFromParallelFor(self, node):
        pass

    def visit_NOP(self, node):
        pass

    def visit(self, node):
        if isinstance(node, Kernel):
            return self.visit_Kernel(node)
        elif isinstance(node, Pipe):
            return self.visit_Pipe(node)
        elif isinstance(node, CFor):
            return self.visit_CFor(node)
        elif isinstance(node, DoWhile):
            return self.visit_DoWhile(node)
        elif isinstance(node, Assign):
            return self.visit_Assign(node)
        elif isinstance(node, CExpr):
            return self.visit_CExpr(node)
        elif isinstance(node, While):
            return self.visit_While(node)
        elif isinstance(node, ForAll):
            return self.visit_ForAll(node)
        elif isinstance(node, For):
            return self.visit_For(node)
        elif isinstance(node, Atomic):
            return self.visit_Atomic(node)
        elif isinstance(node, Exclusive):
            return self.visit_Exclusive(node)
        elif isinstance(node, Block):
            return self.visit_Block(node)
        elif isinstance(node, CBlock):
            return self.visit_CBlock(node)
        elif isinstance(node, Module):
            return self.visit_Module(node)
        elif isinstance(node, Invoke):
            return self.visit_Invoke(node)
        elif isinstance(node, Iterate):
            return self.visit_Iterate(node)
        elif isinstance(node, ReturnFromParallelFor):
            return self.visit_ReturnFromParallelFor(node)
        elif isinstance(node, MethodInvocation):
            return self.visit_MethodInvocation(node)
        elif isinstance(node, If):
            return self.visit_If(node)
        elif isinstance(node, Retry):
            return self.visit_Retry(node)
        elif isinstance(node, NOP):
            return self.visit_NOP(node)
        elif isinstance(node, Names):
            return self.visit_Names(node)
        else:
            assert False, "Unrecognized: (%s) %s" % (node.__class__.__name__, node,)

        # why all the returns?

    def visit2(self, compiler, node):
        self.compiler = compiler
        return self.visit(node)

    def visit3(self, compiler, node, gen):
        self.gen = gen
        return self.visit2(compiler, node)

    def visit4(self, compiler, unit, node, gen):
        self.unit = unit
        return self.visit3(compiler, node, gen)

class ASTWalkerCtx(ASTWalker):
    class_ctx_mgrs = None
    ctx_mgrs = None
    context = None

    def __init__(self, ctx_mgrs = None):
        assert not (self.class_ctx_mgrs or ctx_mgrs)

        self.ctx_mgrs = []

        if self.class_ctx_mgrs is not None:
            for cm in self.class_ctx_mgrs:
                self.ctx_mgrs.append(cm())

        self.ctx_mgrs += ctx_mgrs

        self.context = WalkerContext()
        for m in self.ctx_mgrs:
            m.init_ctx(self.context)

    def enter_node_ctx(self, node):
        for m in self.ctx_mgrs:
            m.enter_node_ctx(node, self.ctx)

    def exit_node_ctx(self, node):
        for m in self.ctx_mgrs:
            m.exit_node_ctx(node, self.ctx)
        
    def visit(self, node):
        self.enter_node_ctx(node)
        x = super(ASTWalkerCtx, self).visit(node)
        self.exit_node_ctx(node)
        
        return x

class ASTPreOrderWalker(ASTWalker):
    def generic_node_visitor(self, node):
        return True

    def generic_node_exit(self, node):
        pass

    def visit_Module(self, node):
        if self.generic_node_visitor(node):
            return super(ASTPreOrderWalker, self).visit_Module(node)

    def visit_Kernel(self, node):
        if self.generic_node_visitor(node):
            super(ASTPreOrderWalker, self).visit_Kernel(node)

    def visit_Pipe(self, node):
        if self.generic_node_visitor(node):
            super(ASTPreOrderWalker, self).visit_Pipe(node)

    def visit_While(self, node):
        if self.generic_node_visitor(node):
            super(ASTPreOrderWalker, self).visit_While(node)

    def visit_DoWhile(self, node):
        if self.generic_node_visitor(node):
            super(ASTPreOrderWalker, self).visit_DoWhile(node)

    def visit_ForAll(self, node):
        if self.generic_node_visitor(node):
            super(ASTPreOrderWalker, self).visit_ForAll(node)

    def visit_CFor(self, node):
        if self.generic_node_visitor(node):
            super(ASTPreOrderWalker, self).visit_CFor(node)

    def visit_For(self, node):
        if self.generic_node_visitor(node):
            super(ASTPreOrderWalker, self).visit_For(node)

    def visit_If(self, node):
        if self.generic_node_visitor(node):
            super(ASTPreOrderWalker, self).visit_If(node)

    def visit_Atomic(self, node):
        if self.generic_node_visitor(node):
            super(ASTPreOrderWalker, self).visit_Atomic(node)

    def visit_Retry(self, node):
        if self.generic_node_visitor(node):
            super(ASTPreOrderWalker, self).visit_Retry(node)

    def visit_Exclusive(self, node):
        if self.generic_node_visitor(node):
            super(ASTPreOrderWalker, self).visit_Exclusive(node)

    def visit_CBlock(self, node):
        if self.generic_node_visitor(node):
            super(ASTPreOrderWalker, self).visit_CBlock(node)

    def visit_Block(self, node):
        if self.generic_node_visitor(node):
            super(ASTPreOrderWalker, self).visit_Block(node)

    def visit_Invoke(self, node):
        if self.generic_node_visitor(node):
            super(ASTPreOrderWalker, self).visit_Invoke(node)

    def visit_Iterate(self, node):
        if self.generic_node_visitor(node):
            super(ASTPreOrderWalker, self).visit_Iterate(node)

    def visit_MethodInvocation(self, node):
        if self.generic_node_visitor(node):
            super(ASTPreOrderWalker, self).visit_MethodInvocation(node)

    def visit_ReturnFromParallelFor(self, node):
        if self.generic_node_visitor(node):
            super(ASTPreOrderWalker, self).visit_ReturnFromParallelFor(node)

    def visit_NOP(self, node):
        pass

    def visit_Names(self, node):
        if self.generic_node_visitor(node):
            super(ASTPreOrderWalker, self).visit_Names(node)

    def visit(self, node):
        if isinstance(node, Kernel):
            self.visit_Kernel(node)
        elif isinstance(node, Pipe):
            self.visit_Pipe(node)
        elif isinstance(node, CFor):
            self.visit_CFor(node)
        elif isinstance(node, Assign):
            return self.visit_Assign(node)
        elif isinstance(node, CExpr):
            return self.visit_CExpr(node)
        elif isinstance(node, DoWhile):
            self.visit_DoWhile(node)
        elif isinstance(node, While):
            self.visit_While(node)
        elif isinstance(node, ForAll):
            self.visit_ForAll(node)
        elif isinstance(node, For):
            self.visit_For(node)
        elif isinstance(node, Atomic):
            self.visit_Atomic(node)
        elif isinstance(node, Exclusive):
            self.visit_Exclusive(node)
        elif isinstance(node, Block):
            self.visit_Block(node)
        elif isinstance(node, CBlock):
            self.visit_CBlock(node)
        elif isinstance(node, Module):
            self.visit_Module(node)
        elif isinstance(node, Invoke):
            self.visit_Invoke(node)
        elif isinstance(node, Iterate):
            self.visit_Iterate(node)
        elif isinstance(node, ReturnFromParallelFor):
            self.visit_ReturnFromParallelFor(node)
        elif isinstance(node, MethodInvocation):
            self.visit_MethodInvocation(node)
        elif isinstance(node, If):
            self.visit_If(node)
        elif isinstance(node, Retry):
            self.visit_Retry(node)
        elif isinstance(node, NOP):
            return self.visit_NOP(node)
        elif isinstance(node, Names):
            return self.visit_Names(node)
        else:
            assert False, "Unrecognized: (%s) %s" % (node.__class__.__name__, node,)

        self.generic_node_exit(node)

class ASTPreOrderWalkerST(ASTPreOrderWalker):
    symtab = None

    def __init__(self):
        self.symtab = Stack()

    def visit(self, node):
        if isinstance(node, BlockStatements):
            self.symtab.push(node.symtab)
            x = super(ASTPreOrderWalkerST, self).visit(node)
            self.symtab.pop()
        else:
            x = super(ASTPreOrderWalkerST, self).visit(node)

        return x

class Dumper(ASTWalker):
    tabbing = 0

    def print_ln(self, s):
        print(("    " * self.tabbing) + s)

    def visit_Module(self, node):
        self.print_ln("Module")

        self.visit(node.stmts)

    def begin_block(self):
        self.tabbing += 1

    def end_block(self):
        self.tabbing -= 1

    def visit_DoWhile(self, node):
        self.print_ln("Do")

        self.visit(node.stmts)

        self.print_ln("While (%s)" % (node.cond))

    def visit_While(self, node):
        self.print_ln("While(%s)" % (node.cond))

        self.visit(node.stmts)

        self.print_ln("End While")
        
    def visit_Pipe(self, node):
        self.print_ln("Pipe%s" % (" once" if node.once else ""))

        self.visit(node.stmts)
                      
    def visit_Kernel(self, node):
        self.print_ln("")
        self.print_ln("Kernel %s args %s" % (node.name, node.args))

        self.visit(node.stmts)

    def visit_ForAll(self, node):
        self.print_ln("ForAll %s in %s" % (node.ndxvar_name, 
                                           node.iterator))
        self.visit(node.stmts)

    def visit_For(self, node):
        self.print_ln("For %s in %s" % (node.ndxvar_name, 
                                        node.iterator))

        self.visit(node.stmts)

    def visit_If(self, node):
        self.print_ln("If (%s) Then" % (node.cond,))

        self.visit(node.true_stmts)
        self.visit(node.false_stmts)

    def visit_ReturnFromParallelFor(self, node):
        self.print_ln("ReturnFromParallelFor(%s)" % (node.value))

    def visit_Atomic(self, node):
        self.print_ln("Atomic %s" % (node.lock,))

        self.visit(node.stmts)
        self.print_ln("Else")
        self.visit(node.fail_stmts)

    def visit_Exclusive(self, node):
        self.print_ln("Exclusive %s" % (node.to_lock,))
        self.visit(node.stmts)
        self.print_ln("Else")
        self.visit(node.fail_stmts)
    
    def visit_Invoke(self, node):
        self.print_ln("Invoke %s(%s)" % (node.kernel, ", ".join(node.args)))

    def visit_Iterate(self, node):
        if node.condition == "WL":
            self.print_ln("Iterate WL %s %s" % (node.kernel, 
                                                node.kernel_args ))
        else:
            self.print_ln("Iterate %s %s %s" % (node.condition, node.kernel,
                                                node.kernel_args))
            
        self.visit(node.stmts)

    def visit_Block(self, node):
        self.begin_block()
        for s in node.stmts:
            self.visit(s)
        self.end_block()

    def visit_CBlock(self, node):
        if isinstance(node, CDecl):
            self.visit_CDecl(node)
            return

        for s in node.stmts:
            self.print_ln(str(s))

    def visit_CDecl(self, node):
        for i in node.decls:
            self.print_ln("%s %s %s" % (i[0], i[1], i[2]))

    def visit_MethodInvocation(self, node):
        self.print_ln("%s.%s %s" % (node.obj_type, node.method, node.args))

    def _visit_anno(self, node):
        #self.print_ln(str(vars(node.anno))) # TODO
        pass

    def visit(self, node):
        self._visit_anno(node)
        super(Dumper, self).visit(node)

def dump_ast(ast):
    d = Dumper()
    d.visit(ast)

if __name__ == "__main__":
    import sys
    f = sys.argv[1]
    ast = parse_input(f)

    dump_ast(ast)

