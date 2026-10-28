import gg.ast.modifier
import gg.ast.walkers
import gg.ast
import gg.passes
import gg.ast.anno
import gg.closure
from collections import namedtuple
import gg.lib.wl
import gg.lib.graph
import gg.types
from gg.ast.utils import Stack
import re

AS_GPU = "gpu"
AS_CPU = "cpu"

StateVar = namedtuple('StateVar', ['name', 
                                   'size', 
                                   'addrspace', 
                                   'argpos',
                                   'ty'])

class StateSaverAnno(gg.ast.anno.ASTNodeAnno):
    """Annotation on Kernel nodes to save arguments"""
    clonable = False
    state_vars = None
    unhandled_vars = None
    array_vars = None

    def __str__(self):
        sv = []
        uv = []
        av = []

        if self.state_vars:
            sv = ["name=%s argpos=%d size=%s addrspace=%s ty=%s" % (s.name, s.argpos, s.size, s.addrspace, s.ty) 
                  for s in self.state_vars]

        if self.unhandled_vars:
            uv = ["name=%s argpos=%d ty=%s" % (s.name, s.argpos, s.ty) for s in self.unhandled_vars]

        if self.array_vars:
            av = ["name=%s argpos=%d ty=%s" % (s.name, s.argpos, s.ty) for s in self.array_vars]
        
        return "\t".join([name + ": " + ", ".join(v) for name, v in [('state', sv), ('array', av), ('unhandled', uv)]])


class SharedVarArgAnno(gg.ast.anno.ASTNodeAnno):
    """Annotation about shared vars on an invoke/iterate"""
    clonable = False
    shared_vars = None

    def __str__(self):
        return "SharedVarAnno(%s)" % (["%s:%s" % (pos, name) for (pos, name) in self.shared_vars])


class PipeAnno(gg.ast.anno.ASTNodeAnno):
    """Annotation on Pipe/Iterate"""
    clonable = False
    depth = None
    index = None # TODO: this should be index within pipe?

    def __str__(self):
        return "PipeAnno(depth=%d, index=%d)" % (self.depth, self.index)

# probably pull this out to a more general routine
class PipeAnnotator(gg.ast.walkers.ASTWalker):
    pipes = None
    index = None

    def visit_Pipe(self, node):
        if not node.has_anno("pipe_anno"):
            node.anno.pipe_anno = PipeAnno(depth = len(self.pipes), index = self.index)

        self.pipes.push(node)
        self.index += 1
        super(PipeAnnotator, self).visit_Pipe(node)
        self.pipes.pop()

    def visit_Invoke(self, node):
        k = self.unit.kernels[node.kernel]
        if not k.contains_retry:
            return 

        self.index += 1
        node.anno.pipe_anno = PipeAnno(depth = len(self.pipes), index = self.index)

    def visit_Iterate(self, node):
        if not node.has_anno("pipe_anno"):
            node.anno.pipe_anno = PipeAnno(depth = len(self.pipes), index = self.index)

        self.pipes.push(node)
        self.index += 1
        super(PipeAnnotator, self).visit_Iterate(node)
        self.pipes.pop()        

    @staticmethod
    def number_pipes(node, unit):
        x = PipeAnnotator()
        x.unit = unit
        x.pipes = Stack()
        x.index = 0
        x.visit(node)



# FIXME: this should actually be from a parser or from a special SharedArg ASTNode ...
SV_RE = re.compile(r'(?P<var>.+)\.gpu_(rd|wr)_ptr\(.*\)')

# also pull this out to a more general routine
class SharedVarAnnotator(gg.ast.walkers.ASTWalker):
    def _get_shared_vars(self, node):
        out = []

        if isinstance(node, gg.ast.Iterate):
            args = node.kernel_args
        else:
            args = node.args

        for p, a in enumerate(args):
            m = SV_RE.match(a)
            if m:
                out.append((p, m.group('var')))

        return out
                
    def visit_Invoke(self, node):
        if not node.check_gen(self.gen):
            return 

        sv = self._get_shared_vars(node)
        if len(sv):
            node.anno.shvar_anno = SharedVarArgAnno(shared_vars = sv)

    def visit_Iterate(self, node):
        if not node.check_gen(self.gen):
            return 

        super(SharedVarAnnotator, self).visit_Iterate(node)

        sv = self._get_shared_vars(node)
        if len(sv):
            node.anno.shvar_anno = SharedVarArgAnno(shared_vars = sv)

    @staticmethod
    def annotate(compiler, unit, node, gen):
        x = SharedVarAnnotator()
        x.visit4(compiler, unit, node, gen)

        
class KernelStates(gg.ast.walkers.ASTWalker):    
    def visit_Kernel(self, node):
        # TODO: do a more intelligent save/restore of graph node data
        # TODO: support saving edge data?
        has_graph = False
        graph_pos = -1
        for apos, (t, a) in enumerate(node.args):
            if t[0] == '+' and t[-1] == '+':
                has_graph = has_graph or (t == '+Graph+')
                if t == '+Graph+':
                    graph_pos = apos
                continue
            else:
                tt = gg.closure.TypeTraits(t)
                tt.strip_qualifiers()

                if tt.is_primitive():
                    if tt.ty not in ('gfloat_p', 'gint_p'):
                        self.state_vars.append(StateVar(a, 
                                                        'sizeof(' + tt.ty + ')',
                                                        AS_CPU,
                                                        apos,
                                                        tt.ty))
                else:
                    if tt.is_ref():
                        x = gg.closure.TypeTraits(tt.remove_ref())
                        if x.is_primitive():
                            self.array_vars.append(StateVar(a, '', AS_GPU, apos, x.ty))
                        else:
                            self.unhandled_vars.append(StateVar(a, '', AS_GPU, apos, tt.ty))
                    else:
                        self.unhandled_vars.append(StateVar(a, '', AS_GPU, apos, t))

        if has_graph:
            self.state_vars.append(StateVar('+NodeData+', '', AS_GPU, graph_pos, ''))

    @staticmethod
    def get_variables(kernel_node):
        ks = KernelStates()
        ks.state_vars = []
        ks.unhandled_vars = []
        ks.array_vars = []

        ks.visit(kernel_node)
        
        return ks.state_vars, ks.unhandled_vars, ks.array_vars


class StateSaver(gg.ast.walkers.ASTWalker):
    def visit_Kernel(self, node):
        if not node.check_gen(self.gen):
            return node

        if not node.has_anno('statesaver'):
            sv, uv, av = KernelStates.get_variables(node)
            statesaver = StateSaverAnno(state_vars=sv, 
                                        unhandled_vars=uv,
                                        array_vars=av)
            
            node.anno.statesaver = statesaver
            #print "< " + node.name + str(node.anno.statesaver) + " >\n"

        return node

class PipeInstrumentor(gg.ast.modifier.ASTModifier):
    def _iterate_pipe(self, node):
        if self.compiler.options.instrument_mode == 'save':
            stmt = gg.ast.CBlock("instr_pipe_iterate(_instr_trace, %d, %d)" % (node.anno.pipe_anno.depth, node.anno.pipe_anno.index),
                                 parse=False)
            if node.condition == "WL":
                return stmt
            else:
                # restoring and filtering has no idea of count so do not write a match entry when we know loop will exit
                return gg.ast.If("loopc", [stmt])
        else:
            if isinstance(node, gg.ast.Pipe) and node.once:
                # non-once will match this in cond
                return gg.ast.CBlock("assert(instr_match_pipe_iterate(_instr_trace, %d, %d))" % (node.anno.pipe_anno.depth, 
                                                                                                 node.anno.pipe_anno.index),
                                     parse=False)
                
            else:
                return gg.ast.NOP()

    def _exit_pipe(self, node):
        if self.compiler.options.instrument_mode == 'save':
            return gg.ast.CBlock("instr_pipe_exit(_instr_trace, %d, %d)" % (node.anno.pipe_anno.depth, node.anno.pipe_anno.index),
                                 parse=False)
        else:
            return gg.ast.CBlock("assert(instr_match_pipe_exit(_instr_trace, %d, %d))" % (node.anno.pipe_anno.depth, node.anno.pipe_anno.index),
                                 parse=False)

    def visit_Iterate(self, node):
        if not node.check_gen(self.gen):
            return node

        node = super(PipeInstrumentor, self).visit_Iterate(node)

        node.stmts.stmts.insert(0, self._iterate_pipe(node))
        return [node, self._exit_pipe(node)]


    def visit_Pipe(self, node):
        if not node.check_gen(self.gen):
            return node

        node = super(PipeInstrumentor, self).visit_Pipe(node)

        node.stmts.stmts.insert(0, self._iterate_pipe(node))
        return [node, self._exit_pipe(node)]

class WLPushRemover(gg.ast.modifier.ASTModifier):
    def visit_MethodInvocation(self, node):
        if not node.check_gen(self.gen):
            return node

        if isinstance(node, gg.lib.wl.PushMethodInvocation) or (node.obj_type == "Worklist" and node.method == "push_prio"):
            return [gg.ast.CBlock("// WL.push removed", parse=False)]

        return node

class WLPushRemoverPass(gg.passes.Pass):
    depends = set(['KernelPropsPass', 'DesugaringPass'])
    
    def run(self, compiler, unit, gen, pm):
        x = WLPushRemover()
        x.visit3(compiler, unit, unit.ast, gen)
        return True

class KernelFilterAnno(gg.ast.anno.ASTNodeAnno):
    clonable = False
    filtered = None
    size = None

class SaveFilter(gg.ast.modifier.ASTModifier):
    kernel = None
    filtered = False
    oforall = None

    def visit_Kernel(self, node):
        if not node.check_gen(self.gen):
            return node

        if not node.has_anno("statesaver"):
            return node

        if node.has_anno("filter"):
            return node

        self.kernel = node
        self.filtered = False
        self.oforall = None

        node = super(SaveFilter, self).visit_Kernel(node)
        self.kernel = None

        if self.filtered:
            if isinstance(node.outer_forall_iterator, gg.lib.wl.WorklistIterator):
                sz = "wlsize"
            elif isinstance(node.outer_forall_iterator, gg.lib.graph.NodeIterator):
                sz = "nodes"
            elif isinstance(node.outer_forall_iterator, gg.types.RangeIterator):
                sz = "range"
            elif node.outer_forall_iterator is not None:
                sz = "?%s" % (node.outer_forall_iterator)
            else:
                assert False

            node.anno.filter = KernelFilterAnno(filtered = True, size = sz)

        return node

    def _marker(self):
        return gg.ast.CBlock("_filter[%s] = 1" % (self.oforall.ndxvar_name,), parse = False)

    def visit_ForAll(self, node):
        if node.nesting_level == 1:
            self.oforall = node
            
        if not node.check_gen(self.gen):
            return node

        if node.nesting_level == 2:
            self.filtered = True
            return self._marker()

        node = super(SaveFilter, self).visit_ForAll(node)

        return node

    def visit_For(self, node):
        if not node.check_gen(self.gen):
            return node

        if node.nesting_level == 2:
            if isinstance(node.iterator, gg.lib.graph.EdgeIterator):
                self.filtered = True
                return self._marker()
        
        node = super(SaveFilter, self).visit_For(node)

        return node



class SaveFilterPass(gg.passes.Pass):
    depends = set(['StateSaverPass', 'KernelPropsPass'])
    rdepends = set(['PreOptimizationPass'])

    def run(self, compiler, unit, gen, pm):
        x = SaveFilter()
        x.visit3(compiler, unit, unit.ast, gen)
        pm.nodes_generated = True

        return True


class StateSaverPass(gg.passes.Pass):
    depends = set(['SemCheckedASTAvail'])
    rdepends = set(['PreOptimizationPass'])
    
    def run(self, compiler, unit, gen, pm):
        x = StateSaver()
        x.visit4(compiler, unit, unit.ast, gen)

        PipeAnnotator.number_pipes(unit.ast, unit)

        SharedVarAnnotator.annotate(compiler, unit, unit.ast, gen)

        #if compiler.options.instrument_mode == 'save':
        y = PipeInstrumentor()
        y.visit3(compiler, unit, unit.ast, gen)
        pm.nodes_generated = True

        return True
