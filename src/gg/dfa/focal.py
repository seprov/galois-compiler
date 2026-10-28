from gg.dfa.dom import *
import gg.cfg
import gg.dfa.cdep
import logging

logger = logging.getLogger(__name__)

def is_uniform_node(n):
    if hasattr(n.ann, "uniform"):
        #print n.node_id, n.ann.uniform
        return n.ann.uniform
    else:                
        return False

class FocalPointsOld(Dominators):
    "Find the focal points of the CFG, i.e. points where every thread will pass through."

    name = "FOCAL POINTS OLD"
    
    def get_focal_points(self):
        return self.info(self.cfg.exit_node)

    def analyze(self):
        def is_uniform_node(n):
            if hasattr(n.ann, "uniform"):
                return n.ann.uniform
            else:                
                return False

            # if n.join_node() and (not "If" in n.name):
            #     #print n, n.name, n.node_id, "is a join node"
            #     return True
            
            # return False

        super(FocalPoints, self).analyze()

        N = self.all_nodes()
        AllN = set([n.node_id for n in N])

        for n in N:
            if n == self.cfg:
                self.info(n).values.add(n.node_id)
            else:
                #print self.info(n).values
                #self.info(n).values.update(AllN)
                
                # initial values are set of dominators 
                pass

        changed = True
        while changed:
            changed = False
            for n in N:
                if n == self.cfg:
                    continue

                i = self.info(n)

                x = None
                do_union = is_uniform_node(n)

                for p, pi in self.pred(n):
                    if x is None:
                        x = pi.values.copy()
                    else:
                        if not do_union:
                            x = x.intersection(pi.values)
                        else:
                            x = x.union(pi.values)

                x.add(n.node_id)
                #print n.node_id, i.values, x
                if i.values != x:
                    assert len(i.values) <= len(x), "%s < %s" % (i.values, x)
                    changed = True
                    i.values = x

class FocalPoints(FocalPointsOld):
    "Find the focal points of the CFG, i.e. points where every thread will pass through."

    name = "FOCAL POINTS"
    
    def analyze(self, pdom):
        def is_uniform_node(n):
            if hasattr(n.ann, "uniform"):
                #print n.node_id, n.ann.uniform
                return n.ann.uniform
            else:                
                return False

        super(FocalPointsOld, self).analyze()
        idomv = self.immediate()
        pdomv = pdom.immediate()

        N = self.all_nodes()
        ND = self.all_nodes_dict()
        AllN = set([n.node_id for n in N])


        B = set([n.node_id for n in N if is_uniform_node(n)])
        L = set([n.node_id for n in N if n.node_id in B and isinstance(n, gg.cfg.LoopNode)])
        M = set()

        logger.debug("B %s" % (B,))
        logger.debug("L %s" % (L,))

        #print idomv
        for n in N:
            if n.node_id in L: 
                M.add(n.node_id)
            else:
                if n.node_id in idomv:
                    idv = idomv[n.node_id]
                    pdv = pdomv[idv]
                    #print n.node_id, idv, pdv, n.node_id == pdv
                    
                    if pdv == n.node_id and is_uniform_node(ND[idv]):
                        M.add(n.node_id)

                    #print n.node_id, idom[n.node_id], n

        logger.debug("M %s" % (M,))

        for n in N:
            if n == self.cfg:
                self.info(n).values.add(n.node_id)
            else:
                #print self.info(n).values
                #self.info(n).values.update(AllN)
                
                # initial values are set of dominators 
                pass

        changed = True
        while changed:
            changed = False
            for n in N:
                if n == self.cfg:
                    continue

                i = self.info(n)

                x = None
                do_union = n.node_id in M
                #if do_union: print "unioning", n.node_id

                x = None
                for p, pi in self.pred(n):
                    if x is None:
                        x = pi.values.copy()
                    else:
                        if not do_union:
                            x = x.intersection(pi.values)
                        else:
                            x = x.union(pi.values)

                x.add(n.node_id)
                #if do_union: print n.node_id, i.values, x
                if i.values != x:
                    assert len(i.values) <= len(x), "%s < %s" % (i.values, x)
                    changed = True
                    i.values = x

# not really a DFA
class FocalPointsCDep(gg.dfa.DFA):
    "Find the focal points of the CFG using a control dependence graph"

    name = "FOCAL POINTS CDEP"

    def get_focal_points(self):
        x = DFNodeInfo()
        x.values = self._focal_points
        return x

    def analyze(self):
        def walk(nid, visited):
            if nid != -1:
                n = allN[nid]
                #print "uniform node", n, nid
                
            visited.add(nid)
                
            for e in cdep.cdepgrf.edges(nid):
                en = allN[e]
                fp.add(e)
                if is_uniform_node(en) and e not in visited:
                    walk(e, visited)

        cdep = gg.dfa.cdep.ControlDependence(self.cfg)
        cdep._debug = self._debug
        cdep.analyze()
        allN = self.all_nodes_dict()
        
        # propagate non-uniformity, could also be done by checking if
        # back edges of a uniform loop are control dependent on
        # uniform nodes

        changed = True
        while changed:
            changed = False
            for nid in cdep.cdepgrf.nodes():
                if nid == -1: continue
                n = allN[nid]
                if not is_uniform_node(n):
                    for e in cdep.cdepgrf.edges(nid):
                        en = allN[e]
                        if is_uniform_node(en):
                            en.ann.uniform = False
                            changed = True

        fp = set([])

        walk(-1, set([]))
        
        self._focal_points = fp
        self.cdep = cdep


    def analyze2(self, strict = True):
        cdep = gg.dfa.cdep.ControlDependence(self.cfg)
        cdep._debug = self._debug
        cdep.analyze()
        allN = self.all_nodes_dict()
        
        # propagate non-uniformity, could also be done by checking if
        # back edges of a uniform loop are control dependent on
        # uniform nodes
        changed = True
        while changed:
            changed = False
            for nid in cdep.cdepgrf.nodes():
                if nid == -1: continue
                n = allN[nid]
                if is_uniform_node(n) == False:
                    for e in cdep.cdepgrf.edges(nid):
                        en = allN[e]
                        if is_uniform_node(en):
                            #print "setting", e, "to non-uniform", nid
                            en.ann.uniform = False
                            changed = True

        fp = set([])

        for nid in cdep.cdepgrf.nodes():
            if nid != -1:
                n = allN[nid]
                #print nid, n, is_uniform_node(n)

            if strict:
                if nid == -1: 
                    for e in cdep.cdepgrf.edges(nid):
                        en = allN[e]
                        if is_uniform_node(en) or is_uniform_node(en) is None:
                            fp.add(e)

                    continue

                if is_uniform_node(n):
                    fp.add(nid)
            else:
                # this is not as conservative as the
                # definition when the graph contains
                # unstructured flow, primarily because
                # code is placed on edges.
                if nid == -1 or is_uniform_node(n):
                    for e in cdep.cdepgrf.edges(nid):
                        fp.add(e)

        self._focal_points = fp
        self.cdep = cdep


    def _check_paths(self, graph, n, allN, memo):
        """Check that all paths to root from a node have only uniform nodes"""

        if n == -1:
            return True

        if n in memo:
            return memo[n]

        for p in graph.node_parents(n):
            if p != -1:
                if not is_uniform_node(allN[p]):
                    memo[p] = False
                    return False

            check_p = self._check_paths(graph, p, allN, memo)
            if not check_p: 
                memo[p] = False
                return False

        return True
        
    def verify(self, focal_points = None):
        allN = self.all_nodes_dict()

        if focal_points is None:
            focal_points = self._focal_points

        problematic = set([])
        memo = {}
        for p in focal_points:            
            p_v = self._check_paths(self.cdep.cdepgrf, p, allN, memo)
            if not p_v: problematic.add(p)

        return problematic

                    
    def dump_cdg(self, f):
        allN = self.all_nodes_dict()

        print("digraph {", file=f)
        for nid in self.cdep.cdepgrf.nodes():
            style = []
            props = ["shape=rect"]
            if nid != -1:
                n = allN[nid]

                if is_uniform_node(n):
                    style.append('rounded')
                
                if nid in self._focal_points:
                    style.append('filled')
                    props.append('fillcolor=yellow')
            else:
                style.append('rounded')

            if len(style):
                style = 'style="' + ",".join(style) + '"'
                props.append(style)

            print(nid, '[%s];' % (",".join(props)), file=f)
                        
            for e in self.cdep.cdepgrf.edges(nid):
                print("%d -> %d;" % (nid, e), file=f)

        print("}", file=f)
        f.close()
