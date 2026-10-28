import gg.cfg

class DFNodeInfo(object):
    values = None

    def __init__(self):
        self.values = set()

class DFA(object):
    "Data-flow Analysis on CFG Skeleton"

    def __init__(self, cfg):
        self.sets = {}
        self.cfg = cfg
        self._all_nodes = []
        self._all_nodes_dict = {}
        self._debug = 0 # positive values increase debugging

    def info(self, node):
        if node.node_id not in self.sets:
            self.sets[node.node_id] = DFNodeInfo()

        return self.sets[node.node_id]
        
    def pred(self, node):
        for p in node.parents:
            yield p, self.info(p)

    def succ(self, node):
        for c in node.children:
            yield c, self.info(c)

    def all_nodes(self):
        x = self._all_nodes
        def add_node(n):
            x.append(n)

        if not x:
            gg.cfg.visitor(self.cfg, add_node, None, set())

        return x

    def all_nodes_dict(self):
        x = self._all_nodes_dict
        def add_node(n):
            x[n.node_id] = n

        if not x:
            gg.cfg.visitor(self.cfg, add_node, None, set())

        return x

    def analyze(self):
        pass

    def dump(self, f):
        print(self.name, file=f)
        N = self.all_nodes()
        for n in N:
            print("  ", n.name, n.node_id, self.info(n).values, file=f)
        print("", file=f)
