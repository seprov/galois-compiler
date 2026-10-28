import gg.ast.walkers
from pycparser import CParser, c_ast
from gg.ast import CBlock
from . import cblocks2
import itertools

DEBUG = 1

class ClosureEnvironment(gg.ast.walkers.ASTPreOrderWalkerST):
    def generic_node_visitor(self, node):
        if hasattr(node, 'c_ast'):
            # lookup against correct symbol table            
            st = self.symtab.top
            self.complete = self.complete and not node.c_ast_incomplete

            if node.c_ast_incomplete:
                self.compiler.log.debug("'%s' has an incomplete C ast during closure environment computation" % (node.__class__.__name__,))            
            for symbol in itertools.chain(node.reads, node.writes):
                if hasattr(self.top_node, 'declares') and symbol in self.top_node.declares:
                    continue

                x = self.top_node.symtab.lookup(symbol)
                e = st.lookup(symbol)

                if x is None and e is not None:
                    # symbol is defined within closure
                    continue

                if e:
                    if not e.builtin:
                        if e.ty not in ('#const', '#define'):
                            self.env[symbol] = e
                    elif symbol == "tid":
                        self.env[symbol] = e

                    if hasattr(self, 'reads'):
                        if symbol in node.reads:
                            self.reads.add(symbol)

                        if symbol in node.writes:
                            self.writes.add(symbol)
                else:
                    if hasattr(node, "parse") and not node.parse:
                        pass
                    else:
                        assert False, "'%s' is undefined" % (symbol,)

        return True

    def get_environment(self, compiler, node):
        self.top_node = node
        self.env = {}
        self.complete = True
        
        self.visit2(compiler, node)
        return self.complete, self.env

    def get_environment_rw(self, compiler, node):
        self.reads = set()
        self.writes = set()

        complete, env = self.get_environment(compiler, node)

        return complete, env, self.reads, self.writes
     
class CReadWriteSets(gg.ast.walkers.ASTPreOrderWalker):
    def generic_node_visitor(self, node):
        if hasattr(node, 'c_ast') and node.check_gen(self.gen):
            node.reads = set()
            node.writes = set()

            node.origin_reads = {}
            node.origin_writes = {}

            #if isinstance(node, CBlock):
            #    print node.stmts
            #    print node.c_ast

            expr = dict(node.c_expr())

            for n, a in node.c_ast.items():
                if not isinstance(a, list): # skip top-level decls?
                    # TODO: attach this to the node itself?
                    v = cblocks2.LinearizeC()
                    v.visit(a)
                    
                    for b in v.lin_blocks:
                        #b.dump()
                        rs, ws = b.rw_set()

                        node.reads = node.reads.union(rs)
                        node.writes = node.writes.union(ws)

                        for r in rs:
                            if r not in node.origin_reads:
                                node.origin_reads[r] = set()

                            node.origin_reads[r].add(n)
                        
                        for w in ws:
                            if w not in node.origin_writes:
                                node.origin_writes[w] = set()

                            node.origin_writes[w].add(n)
                    
                    if self.compiler.show_cgen(self.gen):
                        self.compiler.log.debug("RWSets: '%s' R:%s    W:%s" % (expr[n], node.reads, node.writes))

        return True
            

if __name__ == "__main__":
    import sys
    f = sys.argv[1]
    ast = parse_input(f)
    DEBUG = 1
    d = CBlockParser()
    d.visit(ast)
