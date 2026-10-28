from gg.ast import Kernel
from gg.parser import parse
import gg.ast.walkers

NON_LINEAR_STMTS = set(["ReturnFromParallelFor", "Retry"])

class Stack(object):
    def __init__(self):
        self.stack = []

    def push(self, o):
        self.stack.append(o)
        
    def pop(self):
        return self.stack.pop()

    def top(self):
        return self.stack[-1]

    def empty(self):
        return len(self.stack) == 0

class CfgNodeAnn(object):
    uniform = None

class CfgNode(object):
    def __init__(self, astnode, name, contblock):
        self.name = name
        self.astnode = astnode
        self.children = []
        self.parents = []
        self.block = contblock
        self.ann = CfgNodeAnn()
        self.non_code_edges = set([])  # destinations only, src is implied to be this node,
                                       # this edge may not exist in the graph
        

    def split_node(self):
        return len(self.children) > 1

    def join_node(self):
        return len(self.parents) > 1

    def head_node(self):
        return False

    def tail_node(self):
        return False

# TODO: jump node

class HeadNode(CfgNode):
    def head_node(self):
        return True

class TailNode(CfgNode):
    def tail_node(self):
        return True

class EntryNode(HeadNode):
    pass

class ExitNode(TailNode):
    pass

class ConditionalNode(CfgNode):
    def __init__(self, astnode, name, block):
        super(ConditionalNode, self).__init__(astnode, name, block)
        #self.splitnode = CfgNode(astnode, "%s-split" % (name,))
        self.joinnode = TailNode(astnode, "%s-join" % (name,), block)

        self.joinnode.join_node = lambda: True # TODO: this is due to add_before and true is return

        self.truenode = None
        self.falsenode = None

        if astnode.has_anno("uniform"):
            self.ann.uniform = astnode.anno.uniform.uniform

        self.non_code_edges.add(self.joinnode) # if a direct edge exists to the join node it is non-code

    def head_node(self):
        return True

class LoopNode(CfgNode):
    def __init__(self, astnode, name, block):
        super(LoopNode, self).__init__(astnode, name, block)
        #self.headnode = CfgNode(astnode, "%s-head" % (name,))
        self.tailnode = TailNode(astnode, "%s-tail" % (name,), block)
        if astnode.has_anno("uniform"):
            self.ann.uniform = astnode.anno.uniform.uniform

        self.non_code_edges.add(self.tailnode)

        #self.children.append(self.tailnode)
        #self.tailnode.children.append(self)

        #self.parents.append(self.tailnode)
        #self.tailnode.parents.append(self)

    def head_node(self):
        return True
        
def number_nodes(cfgnode, start = 1):
    no = start

    if not hasattr(cfgnode, 'node_id'):
        cfgnode.node_id = no
        no += 1

    for ch in cfgnode.children:
        if not hasattr(ch, 'node_id'):
            ch.node_id = no
            no += 1
            no = number_nodes(ch, no)

    return no

def check_parents(cfgnode):
    def vnode(n):
        for c in n.children:
            assert n in c.parents, "%s (%d) not in %s (%d)" % (n.name, n.node_id, c.name, c.node_id)

    visitor(cfgnode, vnode, None, set())

def visitor(cfgnode, vnode, vedge, visited):
    if cfgnode.node_id in visited:
        return

    if vnode:
        vnode(cfgnode)

    visited.add(cfgnode.node_id)

    for ch in cfgnode.children:
        if vedge:
            vedge(cfgnode, ch)
        
    for ch in cfgnode.children:
        visitor(ch, vnode, vedge, visited)

def custom_visualize(f, cfgnode, nodefn = None, edgefn = None):
    def vnode(cfgnode):
        if nodefn:
            node_attrs = nodefn(cfgnode)
        else:
            node_attrs = {}

        if len(node_attrs):
            s = ",".join(["%s=%s" % (k, v) for k, v in node_attrs.items()])
            print('%d [%s];' % (cfgnode.node_id, s), file=f)
        else:
            print('%d;' % (cfgnode.node_id,), file=f)

    def vedge(a, b):
        if edgefn:
            edge_attrs = edgefn(a, b)
        else:
            edge_attrs = {}

        if len(edge_attrs):
            s = ",".join(["%s=%s" % (k, v) for k, v in edge_attrs.items()])
            print("%d -> %d [%s];" % (a.node_id, b.node_id, s), file=f)
        else:
            print("%d -> %d;" % (a.node_id, b.node_id), file=f)

    visitor(cfgnode, vnode, vedge, set())

def visualize(f, cfgnode):
    def vnode(cfgnode):
        print('%d [label="%s (%d)"];' % (cfgnode.node_id, cfgnode.name, cfgnode.node_id), file=f)

    def vedge(a, b):
        print("%d -> %d;" % (a.node_id, b.node_id), file=f)

    visitor(cfgnode, vnode, vedge, set())

class CfgBuilder(gg.ast.walkers.ASTWalker):
    def __init__(self, module_ast):
        self.module_ast = module_ast
        self.cfgs = []
        self.parents = [] # possibly also a stack
        self.headnode = Stack()
        self.tailnode = Stack()
        self.contblock = Stack()


    def add_at_edge(self, srcnode, dstnode, astnode):
        assert dstnode.node_id not in srcnode.non_code_edges, "Edge (%d, %d) is a non-code edge" % (srcnode.node_id, 
                                                                                                    dstnode.node_id)

        # NOTE: CDecls are in the CFG because they *may* contain code
        # in their initializers.  After/before may not work with
        # CDecls that contain no initializers since later stages will
        # push them to the top of the containing block.
        
        # TODO: maybe rewrite this not to use the add_*_node functions?
        # Not sure how precise or complete those are?

        after, _ = self._can_add_after_node(srcnode)
        before, _ = self._can_add_before_node(dstnode)
        
        if not (after or before):
            if srcnode.node_id == dstnode.node_id:
                # this is a loop stmt with an empty body and the edge is
                # the entry and return from body edge.
                if hasattr(srcnode.astnode, 'stmts'):
                    if len(srcnode.astnode.stmts.stmts) > 0:
                        import sys
                        print("WARNING: nodes not in CFG (%s)" % (srcnode.astnode.stmts.stmts), file=sys.stderr)

                    # should this have been handled by letting Block create an empty cfgnode?
                    srcnode.astnode.stmts.stmts.append(astnode)
                    return

            print(srcnode, dstnode, srcnode.node_id, dstnode.node_id)

        assert after or before, "Unable to figure out where to add node"  # TODO: fix this

        # if both after and before are okay, then which should we prefer? 
        if after:
            self.add_after_node(srcnode, astnode)
        elif before:
            self.add_before_node(dstnode, astnode)

    def _can_add_after_node(self, cfgnode):
        if isinstance(cfgnode, ConditionalNode) or cfgnode.split_node():
            # TODO: also break, return, etc.
            return False, "Can't add after a split node"

        if isinstance(cfgnode, ExitNode):
            return False, "Can't add after Exit node"

        return True, ""        

    def _can_add_before_node(self, cfgnode):
        if cfgnode.join_node():
            return False, "Can't add before a join node"

        if isinstance(cfgnode, EntryNode):
            return False, "Can't add before Entry node"

        return True, ""

    #TODO: technically, this before/after stuff can be simplified if we use edges?
    def add_after_node(self, cfgnode, astnode):
        can_add, msg = self._can_add_after_node(cfgnode)
        assert can_add, msg

        # case Head Node, but not split node
        if cfgnode.head_node():
            assert hasattr(cfgnode.astnode, "stmts"), "%s does not have stmts" % (cfgnode.astnode,)
            cfgnode.astnode.stmts.stmts.insert(0, astnode)
        else:
            assert not isinstance(cfgnode.astnode, gg.ast.Block) # these should not be in the CFG

            # for both tail node and non-head/tail nodes, we need to locate the containing block
            block = cfgnode.block
            assert block is not None,  cfgnode.name
            assert isinstance(block, gg.ast.Block), block

            idx = block.stmts.index(cfgnode.astnode)
            block.stmts.insert(idx+1, astnode)

    def add_before_node(self, cfgnode, astnode):
        can_add, msg = self._can_add_before_node(cfgnode)
        assert can_add, msg

        # case tail Node, but not join node
        if cfgnode.tail_node():            
            assert hasattr(cfgnode.astnode, "stmts"), "%s does not have stmts" % (cfgnode.astnode,)
            cfgnode.astnode.stmts.stmts.append(astnode)
        else:
            assert not isinstance(cfgnode.astnode, gg.ast.Block) # these should not be in the CFG

            # for both head node and non-head/tail nodes, we need to locate the containing block
            block = cfgnode.block
            assert block is not None,  cfgnode.name
            assert isinstance(block, gg.ast.Block), block
            
            try:
                idx = block.stmts.index(cfgnode.astnode)
            except ValueError:
                print(cfgnode.astnode, cfgnode.astnode._coop_only)
                print(block.stmts)
                for s in block.stmts:
                    print(" ", s)
                print()
                raise

            block.stmts.insert(idx, astnode)

    def add_to_parents(self, cfgnode, make_parent = True):
        for p in self.parents:
            if p.name not in NON_LINEAR_STMTS:
                p.children.append(cfgnode)
                cfgnode.parents.append(p)

        if make_parent:
            self.parents = [cfgnode]

    def all_nodes(self, cfg):
        x = []
        def add_node(n):
            x.append(n)

        if not x:
            visitor(cfg, add_node, None, set())

        return x

    def visit_Module(self, node):
        for s in node.stmts.stmts:
            if isinstance(s, Kernel):
                self.visit(s)
                self.cfgs.append(self.entry_node)
                self.entry_node = None

    def visit_Kernel(self, node):
        self.entry_node = EntryNode(node, "Entry-%s" % (node.name,), None)
        self.exit_node = ExitNode(node, "Exit", None)
        self.entry_node.exit_node = self.exit_node

        self.add_to_parents(self.entry_node)
        super(CfgBuilder, self).visit_Kernel(node)
        self.add_to_parents(self.exit_node)
        self.parents = []

    def visit_If(self, node):
        # TODO: Do not add to children of ReturnFromParallelFor

        n = ConditionalNode(node, "If", self.contblock.top())
        self.add_to_parents(n)
        
        self.visit(node.true_stmts)
            
        true_nodes = self.parents
        self.parents = [n]

        self.visit(node.false_stmts)
        
        self.add_to_parents(n.joinnode)
        for t in true_nodes:
            if t.name not in NON_LINEAR_STMTS:
                t.children.append(n.joinnode)
                n.joinnode.parents.append(t)

    def visit_Atomic(self, node):
        n = ConditionalNode(node, "Atomic", self.contblock.top())
        self.add_to_parents(n)
        
        self.visit(node.stmts)

        true_nodes = self.parents
        self.parents = [n]

        self.visit(node.fail_stmts)
        
        self.add_to_parents(n.joinnode)
        for t in true_nodes:
            if t.name not in NON_LINEAR_STMTS:
                t.children.append(n.joinnode)
                n.joinnode.parents.append(t)

    def visit_Exclusive(self, node):
        n = ConditionalNode(node, "Exclusive", self.contblock.top())
        self.add_to_parents(n)
        
        self.visit(node.stmts)
            
        true_nodes = self.parents
        self.parents = [n]

        self.visit(node.fail_stmts)
        
        self.add_to_parents(n.joinnode)
        for t in true_nodes:
            if t.name not in NON_LINEAR_STMTS:
                t.children.append(n.joinnode)
                n.joinnode.parents.append(t)

    def visit_While(self, node):
        n = LoopNode(node, "While", self.contblock.top())
        self.add_to_parents(n) 

        self.headnode.push(n) # as target for continues
        self.tailnode.push(n.tailnode) # as target for breaks

        super(CfgBuilder, self).visit_DoWhile(node)
        
        # loop back to the head node
        self.add_to_parents(n)

        # stuff outside do-while will descend from tailnode
        self.add_to_parents(n.tailnode)

        self.headnode.pop()
        self.tailnode.pop()

    def visit_DoWhile(self, node):
        n = LoopNode(node, "DoWhile", self.contblock.top())
        self.add_to_parents(n) 

        self.headnode.push(n) # as target for continues
        self.tailnode.push(n.tailnode) # as target for breaks

        super(CfgBuilder, self).visit_DoWhile(node)
        
        # loop back to the head node
        self.add_to_parents(n)

        # stuff outside do-while will descend from tailnode
        self.add_to_parents(n.tailnode)

        self.headnode.pop()
        self.tailnode.pop()
    
    def visit_ForAll(self, node):
        n = LoopNode(node, "ForAll", self.contblock.top())
        
        self.add_to_parents(n) 
        
        # removes precision ?
        self.headnode.push(n) # as target for continues
        self.tailnode.push(n.tailnode) # as target for breaks

        super(CfgBuilder, self).visit_ForAll(node)
        
        # loop back to the head node
        self.add_to_parents(n)

        # stuff outside forloop will descend from tailnode
        self.add_to_parents(n.tailnode)


        self.headnode.pop()
        self.tailnode.pop()

    def visit_CFor(self, node):
        n = LoopNode(node, "CFor", self.contblock.top())
        
        self.add_to_parents(n) 
        
        # removes precision ?
        self.headnode.push(n) # as target for continues
        self.tailnode.push(n.tailnode) # as target for breaks

        super(CfgBuilder, self).visit_CFor(node)
        
        # loop back to the head node
        self.add_to_parents(n)

        # stuff outside forloop will descend from tailnode
        self.add_to_parents(n.tailnode)

        self.headnode.pop()
        self.tailnode.pop()

    def visit_Block(self, node):
        if not self.contblock.empty():
            top = self.contblock.top()
        else:
            top = None

        #n = CfgNode(node, "Block", top)
        #self.add_to_parents(n)
        self.contblock.push(node)
        super(CfgBuilder, self).visit_Block(node)
        self.contblock.pop()

    def visit_Assign(self, node):
        n = CfgNode(node, "Assign", self.contblock.top())
        self.add_to_parents(n)

    def visit_CBlock(self, node):
        n = CfgNode(node, "CBlock", self.contblock.top())
        # assume CBlock is straight-line code

        self.add_to_parents(n)

    def visit_Invoke(self, node):
        n = CfgNode(node, "Invoke", self.contblock.top())
        self.add_to_parents(n)

    def visit_Iterate(self, node):
        n = LoopNode(node, "Iterate", self.contblock.top())
        self.add_to_parents(n)

        self.headnode.push(n)
        self.tailnode.push(n.tailnode)
        super(CfgBuilder, self).visit_Iterate(node)

        self.tailnode.pop()
        self.headnode.pop()

        self.add_to_parents(n)        
        self.add_to_parents(n.tailnode)

    def visit_Pipe(self, node):
        if node.once:
            n = CfgNode(node, "Pipe-Once", self.contblock.top())
            self.add_to_parents(n)
            
            self.visit(node.stmts)
        else:
            n = LoopNode(node, "Pipe-Loop", self.contblock.top())
            self.add_to_parents(n)
            self.headnode.push(n)
            self.tailnode.push(n.tailnode)
            
            self.visit(node.stmts)

            self.tailnode.pop()
            self.headnode.pop()

            self.add_to_parents(n)        
            self.add_to_parents(n.tailnode)

    def visit_MethodInvocation(self, node):
        n = CfgNode(node, "MethodInvocation", self.contblock.top())
        self.add_to_parents(n)

    def visit_ReturnFromParallelFor(self, node):
        n = CfgNode(node, "ReturnFromParallelFor", self.contblock.top())
        self.add_to_parents(n)
        n.children.append(self.exit_node)
        self.exit_node.parents.append(n)

    def visit_Retry(self, node):
        n = CfgNode(node, "Retry", self.contblock.top())
        self.add_to_parents(n)
        n.children.append(self.exit_node)
        self.exit_node.parents.append(n)
        
def make_cfg(ast):
    cb = CfgBuilder(ast)
    cb.visit(ast)
    return cb

if __name__ == "__main__":
    import sys
    f = sys.argv[1]
    ast = parse(f)

    cb = CfgBuilder(ast)
    cb.visit(ast)
    for c in cb.cfgs:
        number_nodes(c)

    for c in cb.cfgs:
        a = set()
        f = c.name + ".dot"
        print(f)
        of = open(f, "w")
        print("digraph {", file=of)
        visualize(of, c)
        print("}", file=of)
        of.close()

    
