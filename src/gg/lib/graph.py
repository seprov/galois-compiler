import gg.types
import gg.ast.params
from gg.ast import MethodInvocation

class NodeIterator(gg.types.Iterator):
    def __init__(self, graph_expr, offset = None, limit = None):
        super(NodeIterator, self).__init__(offset, limit)

        self.graph = graph_expr
    #self.iter_var = iter_var
    #self.current_obj = NodeType(self)
    
    def iter_type(self):
        return "index_type"

    def end(self):
        if self.limit:
            return self.limit
        else:
            return "(%s).nnodes" % (self.graph,)

    def size(self):
        # this should be some AST type
        if self.start() != "0" or self.limit:
            return "(%s) - (%s)"  % (self.end(), self.start())
        else:
            return "(%s).nnodes"  % (self.graph)

    def __str__(self):
        return "%s.nodes()" % (self.graph)

class EdgeIterator(gg.types.Iterator):
    def __init__(self, graph_expr, node_expr, offset = None, limit = None):
        # offset and limit are *relative* 
        super(EdgeIterator, self).__init__(offset, limit)

        self.node = node_expr
        self.graph = graph_expr

    def iter_type(self):
        return "index_type"

    def start(self):
        # using getFirstEdge() delivers more performance than direct access!
        #return "(%s).row_start[%s]" % (self.node.graph, self.node.iter_var)
        if self.offset != "0":
            return "(%s).getFirstEdge(%s) + (%s)" % (self.graph, self.node, self.offset)
        else:
            return "(%s).getFirstEdge(%s)" % (self.graph, self.node)

    def end(self):
        if self.limit:
            return self.start() + "+ %s" % (self.limit,)
        else:
            return "(%s).getFirstEdge((%s) + 1)" % (self.graph, self.node)

    def size(self):
        # this should be some AST type
        if self.offset != "0" or self.limit:
            return "(%s) - (%s)" % (self.end(), self.start())
        else:
            return "(%s).getOutDegree(%s)" % (self.graph, self.node)

    def __str__(self):
        return "%s.edges(%s)" % (self.graph, self.node)

class Graph(gg.types.DataStructure):
    def __init__(self, graph):
        self.graph = graph
        
    def nodes(self, offset=None, limit=None):
        return NodeIterator(self.graph, offset, limit)

    def edges(self, node, offset=None, limit=None):
        return EdgeIterator(self.graph, node, offset, limit)

    def valid_node(self, node):
        return MethodInvocation(self.graph, "valid_node", "Graph", [node]) # TODO: this must take into account offset, limit

    def param(self, ref = False):
        return gg.ast.params.GraphParam(self.graph, ref)

# class NodeType(Type):
#     def __init__(self, parent_iterator):
#         self.par = parent_iterator

#     def data(self, index_expr):
#         return "(%s).node_data[%s]" % (self.par.graph, 
#                                        self.par.iter_var)


# class EdgeType(Type):
#     def __init__(self, parent_iterator):
#         self.par = parent_iterator

#     def data(self):
#         return "(%s).edge_data[%s]" % (self.par.node.graph, 
#                                        self.par.iter_var)

#     def dst(self):
#         return "(%s).edge_dst[%s]" % (self.par.node.graph, 
#                                       self.par.iter_var)
