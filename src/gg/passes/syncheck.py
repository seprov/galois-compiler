import gg.ast.walkers
import gg.ast
import gg.passes
from pycparser import CParser, c_ast
import pycparser
import re

coord_re = re.compile(r"(.*):(\d+):(\d+)")

# The motivation for this pass, in a compiler that accepts ASTs, is
# that the syntax of mostly (hand-written) ASTs must be checked.

class SyntaxChecker(gg.ast.walkers.ASTPreOrderWalker):
    def generic_node_visitor(self, node):
        if hasattr(node, "syntax_types"):
            ds = node.syntax_types()

            x = True
            for attr, (name, ty) in ds.items():
                av = getattr(node, attr)
                
                if ty is gg.ast.Block:
                    av = av.stmts
                    ty = list

                x = self.compiler.check(isinstance(av, ty), 
                                        "%s must be a %s (currently: %s=(%s) %s)" % (name, str(ty), attr, type(av), av), node.__class__.__name__) and x

            if not x:
                return False
                
        if hasattr(node, "syntax_check"):
            x = node.syntax_check(self.compiler)            
            assert x is not None, "%s.syntax_check() returned None, should return True or False" % (node.__class__.__name__)
                                    

        return True 


class CSyntaxChecker(gg.ast.walkers.ASTPreOrderWalker):
    in_kernel = False

    def __init__(self):
        self.parser = CParser()
        self.skel = ["typedef int index_type;",  # TODO: import cuda types!
                     "typedef _Bool bool;"
                     "typedef unsigned int uint;",
                     "typedef struct x uint3;",
                     "typedef struct x dim3;"]
        
    def clean_c(self, stmts):
        out = []

        if isinstance(stmts, str):
            stmts = [stmts]

        for s in stmts:
            ss = str(s)
            if ss and ss[0] != "#":
                out.append(ss + ";")

        return out
                
    def get_c(self, stmts):
        out = [] + self.skel
        
        if self.in_kernel:
            out.append("void main(void) {")

        out += self.clean_c(stmts)

        if self.in_kernel:
            out.append("}")

        return out

    def get_ast(self, ast):
        "Remove skel and void main stuff"

        if isinstance(ast, c_ast.FileAST):
            if self.in_kernel:            
                for e in ast.ext:
                    if isinstance(e, c_ast.FuncDef):
                        if e.decl.name == "main":
                            return e.body
            else:
                return ast.ext

        return None

    def generic_node_exit(self, node):
        if isinstance(node, gg.ast.Kernel):
            assert self.in_kernel
            self.in_kernel = False
        
    def generic_node_visitor(self, node):
        if isinstance(node, gg.ast.Kernel):
            self.in_kernel = True

        if not self.in_kernel:
            if isinstance(node, gg.ast.CBlock): 
                if node.parse and not node.decl:
                    self.skel += self.clean_c(node.stmts)

        if node.check_gen(self.gen) and hasattr(node, "c_expr"):
            node.c_ast = {}
            node.c_ast_incomplete = False

            parse = True

            if isinstance(node, gg.ast.CBlock):
                parse = node.parse

            ca = node.c_expr()
            assert ca is not None, node

            x = True
            for (name, value) in ca:
                c_src = self.get_c(value)

                #print "\n".join(c_src)

                try:
                    ast = self.parser.parse("\n".join(c_src))
                    node.c_ast[name] = self.get_ast(ast)

                    #TODO: there is a bug where things like uint3* x get parsed as expressions instead of declarations! We need to check this here.

                    assert node.c_ast[name] is not None, "%s %s %s" % (node, name, value)
                except pycparser.plyparser.ParseError as e:
                    if not parse:
                        node.c_ast_incomplete = True
                        if self.compiler.show_cgen(self.gen):
                            self.compiler.log.debug("Unable to parse '%s' using C99 parser, might inhibit optimizations" % (value,))
                    else:
                        coord = coord_re.match(str(e))
                        assert coord is not None, str(e)
                        f, l, c = coord.group(1), int(coord.group(2)), int(coord.group(3))
                        ol = c_src[l-1]
                        ol = ol[:c-1] + " *<-* " + ol[c-1:]
                        #TODO: log c_src as debug, e

                        x = self.compiler.check(False, 
                                                "Parse error in C code in '%s', offending code is '%s'" % (name, ol), node.__class__.__name__) and x
        return True

class SyntaxCheckerPass(gg.passes.Pass):
    depends = set(['ASTAvail'])
    rdepends = set(['SemCheckedASTAvail'])

    def run(self, compiler, unit, gen, pm):
        w = SyntaxChecker()
        w.visit2(compiler, unit.ast)
        if compiler.errors > 0:
            compiler.info("%d syntax error(s) found. Halting." % (compiler.errors,))
            
        c = CSyntaxChecker()
        c.visit3(compiler, unit.ast, gen)
        if compiler.errors > 0:
            compiler.info("%d syntax error(s) found. Halting." % (compiler.errors,))

        return compiler.errors == 0
