import gg.dfa.dom
import gg.cfg

class SimpleGraph(object):
    def __init__(self):
        self.node_to_edges = {}
        self.parents = {}

    def add_edge(self, a, b):
        if a not in self.node_to_edges:
            self.node_to_edges[a] = set([])
            
        if b not in self.node_to_edges:
            self.node_to_edges[b] = set([])

        if b not in self.parents:
            self.parents[b] = set()

        self.parents[b].add(a)

        self.node_to_edges[a].add(b)

    def nodes(self):
        return self.node_to_edges.keys()

    def edges(self, node):
        return self.node_to_edges[node]

    def node_parents(self, node):
        return self.parents[node]

    def walk_to_root(self, start):
        """Assumes graph is a tree"""

        out = [start]
        while start in self.parents:
            par = self.parents[start]
            assert len(par) <= 1
            start = list(par)[0]
            out.append(start)

        return out

    def common_ancestor(self, a, b):
        # inefficient!
        a2r = self.walk_to_root(a)
        b2r = self.walk_to_root(b)
        
        if len(a2r) > len(b2r):
            shorter = b2r
            longer = a2r
        else:
            shorter = a2r
            longer = b2r

        # the walks share suffixes
        x = len(shorter)
        for i in range(len(shorter)):
            if shorter[i] == longer[-(x - i)]:
                assert shorter[i:] == longer[-(x - i):]
                return shorter[i], a2r, b2r

        assert False

    def dump(self, f):
        #f = open("pdom_" + self.cfg.name + ".dot", "w")
        print >>f, "digraph {"
        for n in self.node_to_edges:
            for e in self.node_to_edges[n]:
                print >>f, "%d -> %d" % (n, e)
        print >>f, "}"

def get_cfg_edges(cfg, pdom):
    """Get edges (m, n) such that n does not post-dominate m"""

    def visit_edge(a, b):
        pdom_n = pdom.info(a).values

        if a.node_id == -1:            
            #print a.node_id, pdom_n, b.node_id
            pass

        if b.node_id not in pdom_n:
            out.append((a.node_id, b.node_id))

    out = []

    gg.cfg.visitor(cfg, None, visit_edge, set())

    return out

class ControlDependence(object):
    def __init__(self, cfg):
        self.cfg = cfg
        self._debug = 0

    def analyze(self):               
        entry = gg.cfg.CfgNode(None, self.cfg.name, "")
        entry.children = [self.cfg, self.cfg.exit_node]
        self.cfg.parents.append(entry)
        self.cfg.exit_node.parents.append(entry)
        entry.node_id = -1
        entry.exit_node = self.cfg.exit_node

        pdom = gg.dfa.dom.PostDominators(entry)
        pdom.analyze()
        pi = pdom.immediate()
        if self._debug > 1:
            print pi

        # find (m, n) in cfg where n does not post-dominate m
        ptree = SimpleGraph()
        for n, pd in pi.iteritems():            
            ptree.add_edge(pd, n)
            
        if self._debug:
            ptree.dump(open("pdom_" + self.cfg.name + ".dot", "w"))

        out = get_cfg_edges(entry, pdom)

        cdepgrf = SimpleGraph()
        # inefficient
        for (m, n) in out:
            common, m2r, n2r = ptree.common_ancestor(m, n)
            walk = n2r[:n2r.index(common)] # index is inefficient ...
            if self._debug:
                print (m, n), common, walk
            
            for wn in walk:
                cdepgrf.add_edge(m, wn)

        cdepgrf.add_edge(-1, self.cfg.exit_node.node_id) # otherwise exit_node doesn't appear in the cdep
        
        if self._debug:
            cdepgrf.dump(open("cdep_" + self.cfg.name + ".dot", "w"))

        self.cfg.parents.remove(entry)
        self.cfg.exit_node.parents.remove(entry)

        self.cdepgrf = cdepgrf
