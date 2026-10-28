#import gg.ast.walkers
from pycparser import CParser, c_ast, c_generator
#from gg.ast import CBlock

def dump_c(node):
    x = c_generator.CGenerator()
    print(x.visit(node))
    
class ASTDumper(c_ast.NodeVisitor):
    """Simple AST Dumper"""

    def __init__(self):
        self.level = 0        
        
    def enter(self):
        self.level += 1
        
    def leave(self):
        self.level -= 1

    def println(self, s):
        print(("  "*self.level) + s)
        
    def _visit_child(self, name, node, empty = "None"):
        self.println(name)
        self.enter()
        if node:
            self.visit(node)
        else:
            self.println(empty)

        self.leave()
    
    def _visit_children(self, name, nodes, empty = "None"):
        self.println(name)
        self.enter()
        if nodes:
            for n in nodes:
                self.visit(n)
        else:
            self.println(empty)
        self.leave()

    def visit_ArrayDecl(self, node):
        self._visit_child("type", node.type)
        self._visit_child("dim", node.dim)
        self.println("dim_quals: %s" % (node.dim_quals,))

    def visit_ArrayRef(self, node):
        self._visit_child("name", node.name)
        self._visit_child("subscript", node.subscript)

    def visit_Assignment(self, node):
        self.println("op: %s" % (node.op,))
        self._visit_child("lvalue", node.lvalue)
        self._visit_child("rvalue", node.rvalue)

    def visit_BinaryOp(self, node):
        self.println("op: %s" % (node.op,))
        self._visit_child("left", node.left)
        self._visit_child("right", node.right)

    def visit_Break(self, node):
        pass

    def visit_Case(self, node):
        self._visit_child("expr", node.expr)
        self._visit_children("stmts", node.stmts)

    def visit_Cast(self, node):
        self._visit_child("to_type", node.to_type)
        self._visit_child("expr", node.expr)

    def visit_Compound(self, node):
        self._visit_children("block_items", node.block_items)

    def visit_CompoundLiteral(self, node):
        self._visit_child("type", node.type)
        self._visit_child("init", node.init)

    def visit_Constant(self, node):
        self.println("type: %s" % (node.type,))
        self.println("value: %s" % (node.value,))
        
    def visit_Continue(self, node):
        pass

    def visit_Decl(self, node):
        self.println("name: %s" % (node.name,))
        self.println("quals: %s" % (node.quals,))
        self.println("storage: %s" % (node.storage,))

        self._visit_child("type", node.type)
        self._visit_child("init", node.init)
        self._visit_child("bitsize", node.bitsize)

    def visit_DeclList(self, node):
        self._visit_children("decls", node.decls)

    def visit_Default(self, node):
        self._visit_children("stmts", node.stmts)

    def visit_DoWhile(self, node):
        self._visit_child("cond", node.cond)
        self._visit_child("stmt", node.stmt)

    def visit_EllipsisParam(self, node):
        pass

    def visit_EmptyStatement(self, node):
        pass

    def visit_Enum(self, node):
        self.println("name: %s" % (node.name,))
        self._visit_child("values", node.values)
    
    def visit_EnumeratorList(self, node):
        self._visit_children("enumerators", node.enumerators)

    def visit_ExprList(self, node):
        self._visit_children("exprs", node.exprs)

    def visit_FileAST(self, node):
        self._visit_children("ext", node.ext)

    def visit_For(self, node):
        self._visit_child("init", node.init)
        self._visit_child("cond", node.cond)
        self._visit_child("next", node.__next__)
        self._visit_child("stmt", node.stmt)

    def visit_FuncCall(self, node):
        self._visit_child("name", node.name)
        self._visit_child("args", node.args)
        
    def visit_FuncDecl(self, node):
        self._visit_child("args", node.args)
        self._visit_child("type", node.type)

    def visit_FuncDef(self, node):
        self._visit_child("decl", node.decl)
        self._visit_children("param_decls", node.param_decls, "void")
        self._visit_child("body", node.body)

    def visit_Goto(self, node):
        pass

    def visit_ID(self, node):
        self.println("id: %s" % (node.name,))

    def visit_IdentifierType(self, node):
        self.println("names: %s" % (node.names,))

    def visit_If(self, node):
        self._visit_child("cond", node.cond)
        self._visit_child("iftrue", node.iftrue)
        self._visit_child("iffalse", node.iffalse)

    def visit_InitList(self, node):
        self._visit_children("exprs", node.exprs)

    def visit_Label(self, node):
        self.println("name: %s" % (node.name,))
        self._visit_child("stmt", node.stmt)

    def visit_NamedInitializer(self, node):
        self._visit_children("name", node.name)
        self._visit_children("expr", node.expr)

    def visit_PtrDecl(self, node):
        self.println("quals: %s" % (node.quals,))
        self._visit_child("type", node.type)

    def visit_ParamList(self, node):
        self._visit_children("params", node.params)

    def visit_Return(self, node):
        self._visit_child("expr", node.expr)

    def visit_Struct(self, node):
        self.println("name: %s" % (node.name,))
        self._visit_children("decls", node.decls)

    def visit_StructRef(self, node):
        self._visit_child("name", node.name)
        self.println("type: %s" % (node.type,))
        self._visit_child("field", node.field)

    def visit_Switch(self, node):
        self._visit_child("cond", node.cond)
        self._visit_child("switch", node.switch)

    def visit_TernaryOp(self, node):
        self._visit_child("cond", node.cond)
        self._visit_child("iftrue", node.iftrue)
        self._visit_child("iffalse", node.iffalse)

    def visit_TypeDecl(self, node):
        self.println("declname: %s" % (node.declname,))
        self.println("quals: %s" % (node.quals,))
        self._visit_child("type", node.type)

    def visit_Typedef(self, node):
        self.println("name: %s" % (node.name,))
        self.println("quals: %s" % (node.quals,))
        self.println("storage: %s" % (node.storage,))
        self._visit_child("type", (node.type,))

    def visit_Typename(self, node):
        self.println("name: %s" % (node.name,))
        self.println("quals: %s" % (node.quals,))
        self._visit_child("type", node.type)

    def visit_UnaryOp(self, node):
        self.println("op: %s" % (node.op,))
        self._visit_child("expr", node.expr)

    def visit_Union(self, node):
        self.println("name: %s" % (node.name,))
        self._visit_children("decls", node.decls)

    def visit_While(self, node):
        self._visit_child("cond", node.cond)
        self._visit_child("stmt", node.stmt)

    def visit(self, node):
        self.println("* " + str(node.__class__.__name__))
        super(ASTDumper, self).visit(node)

class LinearC(object):
    def __init__(self, node, linear):
        self.node = node
        self.linear = linear

    def rw_set(self, remove_tmp = True):
        def filter_tmp(names):
            if not remove_tmp:
                return names
            else:
                return set([x for x in names if x[0] != '%'])

        def refs_get(key):
            return refs.get(key, key)

        def deref(names):
            #print names
            last_names = set()
            while len(names) and names != last_names:
                last_names = names
                names = set([(refs[xx] if xx in refs else xx) for xx in names])
                #print names, last_names
            
            return names
                    
        reads = set()
        writes = set()
        refs = {} # only keep top-level refs? handles only PODs?

        for l in self.linear:
            op = l[0]

            if op == "deref":
                refs[l[1]] = refs_get(l[2])
                reads.add(l[2])
            elif op == "struct-ref":
                refs[l[1]] = refs_get(l[2]) # + "." + l[3] # TODO
                reads.add(l[2]) # technically, not a read
            elif op == "array-ref":
                refs[l[1]] = refs_get(l[2])
                reads.add(l[3])
            elif op[:6] == "assign":
                writes.add(l[1])
                reads.add(l[2])
            elif op[:5] == "binop":
                writes.add(l[1])
                reads.add(l[2])
                reads.add(l[3])
            elif op[:4] == "unop":
                writes.add(l[1])
                reads.add(l[2])

                if op[4:] in ("p++", "p--"):
                    # postfix ++ and --
                    writes.add(l[2])                    
            elif op == "cmov":
                writes.add(l[1])
                reads.add(l[2])
                reads.add(l[3])
                reads.add(l[4])
            elif op == "mov":
                writes.add(l[1])
                reads.add(l[2])
            elif op == "call":
                pass # for now
            else:
                assert False, "Unsupported op: %s" % (op,)

        #print refs
        return filter_tmp(deref(reads)), filter_tmp(deref(writes))

        
    def dump(self):
        dump_c(self.node)
        print(self.linear)
        print("  "+"\n  ".join([", ".join(xx) for xx in self.linear]))
        
class LinearizeC(c_ast.NodeVisitor):
    def __init__(self):
        self.tlnode = None
        self.lin = []
        self.lin_blocks = []
        self.tmp = 0
        self.constants = {}

    def begin_lin(self, node):
        if self.tlnode is not None:
            dump_c(self.tlnode)

        assert self.tlnode is None and len(self.lin) == 0, self.lin
        self.tlnode = node
                    
    def end_lin(self):
        if len(self.lin) > 0:
            self.lin_blocks.append(LinearC(self.tlnode, self.lin))
            
        self.tlnode = None
        self.lin = []

    def new_tmp(self, typ = "tmp"):
        self.tmp += 1
        return "%%%s%d" % (typ, self.tmp)

    # def visit_IdentifierType(self, node):
    #     return "%builtin"

    def visit_ID(self, node):
        return node.name

    def visit_Constant(self, node):
        v = str(node.value)
        if v not in self.constants:
            n = self.new_tmp("const")
            self.constants[v] = n
            return n

        return self.constants[v]

    def visit_UnaryOp(self, node):
        if node.op != "sizeof":
            expr = self.visit(node.expr)
        else:
            expr = "%builtin"

        if node.op in ("p++", "p--", "--", "++"):
            if node.op in ('--', '++'):
                val = expr 
            else:
                val = self.new_tmp()
        else:
            val = self.new_tmp()

        self.lin.append(('unop%s' % node.op, val, expr))
        return val

    def visit_Cast(self, node):
        # TODO: encode cast?
        expr = self.visit(node.expr)
        return expr

    def visit_Return(self, node):
        expr = self.visit(node.expr)
        return expr

    def visit_TernaryOp(self, node):
        cond = self.visit(node.cond)
        iftrue = self.visit(node.iftrue)
        iffalse = self.visit(node.iffalse)
        val = self.new_tmp()

        self.lin.append(('cmov', val, cond, iftrue, iffalse))
        return val

    def visit_BinaryOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        val = self.new_tmp()

        self.lin.append(("binop%s" % (node.op), val, left, right))
        return val

    def visit_ArrayRef(self, node):
        array = self.visit(node.name)
        subscript = self.visit(node.subscript)
        val = self.new_tmp()

        self.lin.append(('array-ref', val, array, subscript))
        return val

    def visit_Assignment(self, node):
        lvalue = self.visit(node.lvalue)
        rvalue = self.visit(node.rvalue)
        self.lin.append(('assign%s' % node.op, lvalue, rvalue))

        return lvalue

    def visit_StructRef(self, node):
        val = self.new_tmp()
        name = self.visit(node.name)
        field = self.visit(node.field)

        if node.type == ".":
            self.lin.append(('struct-ref', val, name, field))
        elif node.type == "->":
            val2 = self.new_tmp()
            self.lin.append(('deref', val2, name))
            self.lin.append(('struct-ref', val, val2, field))
        
        return val

    def visit_ExprList(self, node):
        val = ""
        for x in node.exprs:
            expr = self.visit(x)
            val = self.new_tmp()

            self.lin.append(('mov', val, expr))
            
        return val

    def visit_FuncCall(self, node):
        name = self.visit(node.name)

        if node.args:
            
            self.visit(node.args)

        val = self.new_tmp('ret')
        self.lin.append(('call', val, name))

        return val

    def visit_Compound(self, node):
        if node.block_items:
            for bi in node.block_items:
                self.begin_lin(bi)
                x = self.visit(bi)

                if isinstance(bi, c_ast.ID):
                    # handles a name by itself with no operators which
                    # results in no linear code, so we define it to be a read
                    # TODO: is this the only such case?

                    self.lin.append(('mov', self.new_tmp(), x))

                self.end_lin()

    def visit_Decl(self, node):
        if node.init:
            val = self.visit(node.init)
            self.lin.append(('mov', node.name, val))
            
        return node.name        

    def visit_InitList(self, node):
        last_val = ""

        for e in node.exprs:
            expr = self.visit(e)
            val = self.new_tmp()
            self.lin.append(('mov', val, expr))
            last_val = val

        return last_val # not entirely accurate!
            
    def visit(self, node):
        assert node is not None
        x = super(LinearizeC, self).visit(node)

        if x is None and not isinstance(node, (c_ast.Compound, c_ast.Break, c_ast.Continue, c_ast.If, c_ast.EmptyStatement)):
            dump_c_ast(node)
            assert x is not None, node
            
        return x

class ContainsControlFlow(c_ast.NodeVisitor):
   
    @staticmethod
    def get_control_flow(ast):
        x = ContainsControlFlow()
        x.statements = set()

        x.visit(ast)
        
        return x.statements

    def visit_Goto(self, node):
        self.statements.add("goto %s" % (node.name,))

    def visit_Continue(self, node):
        self.statements.add("continue")
    
    def visit_Break(self, node):
        self.statements.add("break")

    
def get_main_body(ast):
    if isinstance(ast, c_ast.FileAST):
        for e in ast.ext:
            if isinstance(e, c_ast.FuncDef):
                if e.decl.name == "main":
                    return e.body

    return None

def dump_c_ast(ast):
    v = ASTDumper()
    v.visit(ast)

if __name__ == "__main__":
    import sys

    f = sys.argv[1]
    fc = open(f, "r").read()

    p = CParser()
    ast = p.parse(fc)
    DEBUG = 1

    ast = get_main_body(ast)
    assert ast is not None
    dump_c(ast)
    dump_c_ast(ast)
    

    d = LinearizeC()
    d.visit(ast)
    print(d.lin_blocks)
    for x in d.lin_blocks:
        x.dump()
        print(x.rw_set())
        print()
    #print ast
