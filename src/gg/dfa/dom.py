from gg.dfa import *

class DomCommon(DFA):
    def imm(self):
        alln = self.all_nodes_dict()

        out = {}

        for nid, n in alln.items():
            x = self.info(n)

            for xdom in x.values:
                if xdom == nid: continue # strict

                for odom in (x.values - set([xdom, nid])):
                    # must not strictly dominate other strict dominators
                    if xdom in self.info(alln[odom]).values:
                        break
                else:
                    out[nid] = xdom
                    break # unique

        return out

    def frontier(self):
        alln = self.all_nodes_dict()

        out = {}

        # textbook defn
        for nid, n in alln.items():
            x = self.info(n)
            #print "NODE", nid
            # succ or pred
            rel = list(self.opp_relfn(n))

            # for each of my dominators
            for xdomid in x.values:
                #print "xdom", xdomid
                # dominance frontier for x
                if xdomid not in out:
                    out[xdomid] = set()
                    
                df_x = out[xdomid]
                
                # do I have any succ (dom) or pred (pdom) that are not dominated by my dominators
                for r, rdom in rel:
                    if xdomid not in rdom.values:
                        #print "adding", r.node_id, "as df for", xdomid
                        df_x.add(r.node_id)
                    else:
                        #print xdomid, "dominates", r.node_id
                        pass

        return out

    def immediate(self):
        out = {}

        allN = self.all_nodes_dict()

        for nid, n in allN.items():
            i = self.info(n).values - set([n.node_id])
            
            for can_imm in i:
                for oth in i:
                    if oth == can_imm: continue

                    oth_values = self.info(allN[oth]).values
                    if can_imm in oth_values: # can_imm dominates oth
                        #print can_imm, oth, oth_values
                        break
                else:
                    out[nid] = can_imm
                    break

        #print out
        return out
       
    def analyze(self):
        N = self.all_nodes()

        self._init_analysis(N)

        changed = True
        while changed:
            changed = False
            for n in N:
                i = self.info(n)

                x = None
                for p, pi in self.relfn(n):
                    if x is None:
                        x = pi.values.copy()
                    else:
                        x = x.intersection(pi.values)

                if x is None:
                    x = set()

                x.add(n.node_id)

                if i.values != x:
                    changed = True
                    i.values = x

class Dominators(DomCommon):
    "Find the dominators of nodes in the CFG"
    name = "DOMINATORS"
    relfn = DomCommon.pred
    opp_relfn = DomCommon.succ

    def _init_analysis(self, N): 
        AllN = set([n.node_id for n in N])

        for n in N:
            if n == self.cfg:
                self.info(n).values.add(n.node_id)
            else:
                self.info(n).values.update(AllN)

class PostDominators(DomCommon):
    "Find the post-dominators of nodes in the CFG"
    name = "POST-DOMINATORS"
    relfn = DomCommon.succ
    opp_relfn = DomCommon.pred

    def _init_analysis(self, N): 
        AllN = set([n.node_id for n in N])

        for n in N:
            if n == self.cfg.exit_node:
                self.info(n).values.add(n.node_id)
            else:
                self.info(n).values.update(AllN)
