import gg.passes
import gg.ast.props
import json

class PropReaderPass(gg.passes.Pass):
    depends = set(['SemCheckedASTAvail'])
    rdepends = set(['PreOptimizationPass'])
    #rdepends = set(['PropWriterPass'])

    def __init__(self, propfile):
        self.propfile = propfile

    def run(self, compiler, unit, gen, pm):
        if gen == 0:
            of = open(self.propfile, "r")
            x = json.loads(of.read())
            r = gg.ast.props.PropsReader()
            r.read_props(unit.ast, x)
            of.close()

        return True

class PropWriterPass(gg.passes.Pass):
    depends = set(['SemCheckedASTAvail'])
    rdepends = set(['PreOptimizationPass'])

    def __init__(self, propfile):
        self.propfile = propfile

    def run(self, compiler, unit, gen, pm):
        if gen == 0:
            of = open(self.propfile, "w")
            w = gg.ast.props.PropsWriter()
            x = w.write_props(unit.ast)
            of.write(json.dumps(x, indent=1))
            of.close()

        return True
