from gg.passes import Pass
import gg.dfa.dom, gg.dfa.focal # TODO
import sys

class GenericDFA(Pass):
    depends = set(['SemCheckedASTAvail'])
    analysis = None

    def __init__(self, dump = False):
        self.dump = dump

    def run(self, compiler, unit):
        for x in unit.cb.cfgs:
            a = self.analysis(x)
            a.analyze()
            if self.dump:
                a.dump(sys.stderr) # TODO

            # TODO: store the results of the analysis with the CFG

        return True

class DominatorsAnalysis(GenericDFA):
    depends = set(['CFGBuilderPass'])
    analysis = gg.dfa.dom.Dominators
    
class FocalPointsAnalysis(GenericDFA):
    depends = set(['CFGBuilderPass'])
    analysis = gg.dfa.focal.FocalPoints
    
        
        
