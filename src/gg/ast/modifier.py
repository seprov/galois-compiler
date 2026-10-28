from gg.ast import *
from gg.ast.utils import Stack

class ASTModifier(object):
    def __init__(self):
        pass

    def _visit_stmts(self, stmts):
        out = []
        for s in stmts:
            r = self.visit(s)
            assert r is not None
            if not isinstance(r, list):
                out.append(r)
            else:
                out += r

        return out
        
    
    def visit_Module(self, node):
        node.stmts = self.visit(node.stmts)
        return node

    def visit_Kernel(self, node):
        node.stmts = self.visit(node.stmts)
        return node

    def visit_Pipe(self, node):
        node.stmts = self.visit(node.stmts)
        return node

    def visit_Assign(self, node):
        #TODO the rules for visiting an expression node are different ...
        node.rhs = self.visit(node.rhs)
        return node
        
    def visit_While(self, node):
        node.stmts = self.visit(node.stmts)
        return node

    def visit_DoWhile(self, node):
        node.stmts = self.visit(node.stmts)
        return node

    def visit_ForAll(self, node):
        node.stmts = self.visit(node.stmts)
        return node

    def visit_CFor(self, node):
        node.stmts = self.visit(node.stmts)
        return node

    def visit_For(self, node):
        node.stmts = self.visit(node.stmts)
        return node

    def visit_If(self, node):
        node.true_stmts = self.visit(node.true_stmts)
        node.false_stmts = self.visit(node.false_stmts)
        return node

    def visit_Atomic(self, node):
        node.stmts = self.visit(node.stmts)
        node.fail_stmts = self.visit(node.fail_stmts)
        return node

    def visit_Retry(self, node):
        return node

    def visit_Exclusive(self, node):
        node.stmts = self.visit(node.stmts)
        node.fail_stmts = self.visit(node.fail_stmts)
        return node

    def visit_Block(self, node):
        node.stmts = self._visit_stmts(node.stmts)
        return node

    def visit_CExpr(self, node):
        return node

    def visit_CBlock(self, node):
        #node.stmts = self._visit_stmts(node.stmts)
        return node

    def visit_Invoke(self, node):
        return node

    def visit_Iterate(self, node):
        node.stmts = self.visit(node.stmts)
        return node

    def visit_MethodInvocation(self, node):
        return node

    def visit_Names(self, node):
        return node

    def visit_ReturnFromParallelFor(self, node):
        return node

    def visit_NOP(self, node):
        return node

    def visit(self, node):
        if isinstance(node, Kernel):
            return self.visit_Kernel(node)
        elif isinstance(node, Pipe):
            return self.visit_Pipe(node)
        elif isinstance(node, CFor):
            return self.visit_CFor(node)
        elif isinstance(node, DoWhile):
            return self.visit_DoWhile(node)
        elif isinstance(node, While):
            return self.visit_While(node)
        elif isinstance(node, Assign):
            return self.visit_Assign(node)
        elif isinstance(node, CExpr):
            return self.visit_CExpr(node)
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
            assert False, "Unrecognized: %s" % (node,)

    def visit2(self, compiler, unit, node):
        self.compiler = compiler
        self.unit = unit

        return self.visit(node)

    def visit3(self, compiler, unit, node, gen):
        self.gen = gen

        return self.visit2(compiler, unit, node)

class ASTModifierST(ASTModifier):
    symtab = None

    def __init__(self):
        self.symtab = Stack()

    def visit(self, node):
        if isinstance(node, BlockStatements):
            if not hasattr(node, 'symtab'):
                print(node, node.name)

            #print "visiting", node
            self.symtab.push(node.symtab)
            x = super(ASTModifierST, self).visit(node)
            self.symtab.pop()
            #print "leaving", node
        else:
            x = super(ASTModifierST, self).visit(node)

        return x

class ASTModifierScoped(ASTModifierST):
    kernel = None
    # TODO: top-level pipe, path, control-dependences, etc?

    def visit(self, node):
        if isinstance(node, Kernel):
            assert self.kernel is None
            self.kernel = node

        x = super(ASTModifierScoped, self).visit(node)

        if isinstance(node, Kernel):
            self.kernel = None

        return x
