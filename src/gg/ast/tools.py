from gg.ast.walkers import *

class EraseGen(ASTPreOrderWalker):
    def generic_node_visitor(self, node):
        node.generation = None
        return True

#TODO: why not use copy.deepcopy()?
# 1. this is a tree, so simpler
# 2. some things we do not want to clone (gen, symtab, etc.)
def clone(node, copy_gen = True):
    n = node.clone()
    if copy_gen:
        n.gen = node.gen

    return n

def clone_list(node, copy_gen = True):
    out = []

    for n in node:
        out.append(clone(n, copy_gen))
        
    return out        
    
Dumper = gg.ast.walkers.Dumper
