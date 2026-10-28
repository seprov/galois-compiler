from gg.backend.cuda.cudagen import CUDAPreGen, CUDAGen
import gg.passes

class CUDACompilerOptions(object):
    worklist_type = "texture"
    graph_type = "texture"
    use_worklist_slots = True   # not exposed to UI

    def set_options(self, args):
        self.worklist_type = args.cuda_worklist
        self.graph_type = args.cuda_graph
        self.use_worklist_slots = not args.cuda_no_slots

        if self.parent.outline_iterate_gb:
            self.worklist_type = 'basic'

    def get_passes(self, outputfile):
        return [CUDAPreGenPass(), CUDAGenPass(outputfile)]

    def __str__(self):
        out = []
        for p, v in vars(self).items():
            if p != "parent":
                out.append("cuda.%s=%s" % (p, v))

        return " $ ".join(out)

# TODO: these are no-going-back-now passes

# this will need to be relocated to a non-backend 
class PopulateEntryExit(gg.ast.walkers.ASTPreOrderWalker):
    def __init__(self):
        self.kernel = None

    def generic_node_exit(self, node):
        if isinstance(node, gg.ast.Kernel):
            self.kernel = None

    def generic_node_visitor(self, node):
        if isinstance(node, gg.ast.Kernel):
            assert self.kernel is None
            self.kernel = node

        if node.check_gen(self.gen):
            if node.has_anno("at_entry_exit"):
                ee = self.kernel.anno.entry_exit
                aee = node.anno.at_entry_exit

                ee.at_entry += aee.at_entry
                ee.at_exit += aee.at_exit
                ee.decls.update(aee.decls)

        return True

class CUDAPreGenPass(gg.passes.Pass):
    depends = set(['PreOutputPass'])

    def run(self, compiler, unit, gen, pm):
        v = PopulateEntryExit()
        v.visit3(compiler, unit.ast, gen)        

        w = CUDAPreGen(unit)
        w.visit2(compiler, unit.ast)
        return True
        
class CUDAGenPass(gg.passes.Pass):
    depends = set(['CUDAPreGenPass'])
    rdepends = set(['PostOutputPass'])

    def __init__(self, outputfile):
        self.outputfile = outputfile

    def run(self, compiler, unit, gen, pm):
        w = CUDAGen(unit)
        w.set_options(compiler, compiler.options.backend)
        if isinstance(self.outputfile, str):
            w.outputfile = open(self.outputfile, "w")
        else:
            w.outputfile = self.outputfile

        w.visit4(compiler, unit, unit.ast, gen)
        return True

def add_backend_arguments(parser):
    cuda_group = parser.add_argument_group("CUDA Backend")
    cuda_group.add_argument('--cuda-worklist', choices=set(['basic', 'texture']), default='texture', help="Choose worklist datatype")
    cuda_group.add_argument('--cuda-graph', choices=set(['basic', 'texture']), default='texture', help="Choose graph datatype")
    cuda_group.add_argument('--cuda-no-slots', action="store_true", help="Do not use worklist slots")


CompilerOptions = CUDACompilerOptions
