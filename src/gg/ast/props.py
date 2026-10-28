import gg.ast
import gg.ast.walkers
from . import utils
from . import anno

# TODO: linear or nested? This is the nested format for now, which has
# advantages, but is also very brittle to path changes.
#
# Moving to linear would require globally unique names.

class PropsWriter(gg.ast.walkers.ASTPreOrderWalker):
    def generic_node_exit(self, node):
        if len(self.path) and self.path.top is node:
            self.path.pop()

            if hasattr(node, "name") and node.name is not None and isinstance(node, gg.ast.BlockStatements):
                self.props.pop()
            
    def generic_node_visitor(self, node):
        self.path.push(node)

        if hasattr(node, "name") and node.name is not None:
            if node.has_anno("scoped_optimizations"):
                opt = node.anno.scoped_optimizations.to_dict()
            else:
                opt = {}
            
            self.props.top[node.name] = {"_optimizations_": opt} # TODO: annotations: {}

            if isinstance(node, gg.ast.BlockStatements):
                self.props.push(self.props.top[node.name])

        return True

    def write_props(self, node):
        self.path = utils.Stack()
        self.props = utils.Stack()
        self.props.push({})
        self.visit(node)
        return self.props.pop()

class PropsReader(gg.ast.walkers.ASTPreOrderWalker):
    def generic_node_exit(self, node):
        if hasattr(node, "name") and node.name is not None and isinstance(node, gg.ast.BlockStatements):
            self.props.pop()
        
    def generic_node_visitor(self, node):
        if hasattr(node, "name") and node.name is not None:
            if node.name not in self.props.top:
                # WARNING? node.name does not have properties
                return True

            props = self.props.top[node.name]
            
            if "_optimizations_" in props:
                po = props["_optimizations_"]
                if not ("_ignore_" in po and po["_ignore_"]) and len(po):
                    # TODO: check the syntax!
                    node = anno.ScopedOptimizations(node)
                    node.anno.scoped_optimizations.from_dict(props['_optimizations_'])

            if isinstance(node, gg.ast.BlockStatements):
                # TODO: if a name is moved from a block statement to
                # another non-block statement then we will have errors.
                self.props.push(props)

        return True

    def read_props(self, node, props):
        self.props = utils.Stack()
        self.props.push(props)
        self.visit(node)

if __name__ == "__main__":
    import sys, json
    f = sys.argv[1]
    ast = parse_input(f)
    DEBUG = 1
    d = PropsWriter()
    x = d.write_props(ast)
    print(json.dumps(x, indent=1))
    
    r = PropsReader()
    r.read_props(ast, x)
