import cgen

from cgen import FunctionBody, \
        FunctionDeclaration, Typedef, POD, Value, \
        Pointer, Module, Block, Initializer, Assign, Include, If
from cgen.cuda import CudaGlobal, CudaDevice, CudaLaunchBounds
import gg.ast
import gg.ast.walkers
import gg.ndxtrans
from gg.ast.params import *
from gg.ast.utils import Stack
from gg.ast.callconfig import ShrinkableBlockTy, FixedBlockTy, ElasticBlockTy
from . import instr as cuda_instr

TOP_LEVEL = (gg.ast.Kernel, gg.ast.CBlock, gg.ast.Names)
WL_TYPES = {'basic': "Worklist2", 'texture': "WorklistT"}
PIPE_TYPE_TEMPLATE = "PipeContextT<%s>"
GRAPH_TYPES = {'basic': 'CSRGraph', 'texture': "CSRGraphTex"}  # or CSRGraph
AOL_TYPES = {'basic': "AppendOnlyList"}

USE_POP_ID_LEN = False

class GenericBlock(object):
    def __init__(self):
        self.decls = []
        self.stmts = []

    def to_block(self):
        o = Block()
        for d in self.decls:
            o.append(d)

        for s in self.stmts:
            if isinstance(s, GenericBlock):
                vs = s.to_block()
                o.append(vs)
            else:
                o.append(s)

        return o

    def add_stmt(self, st_str):
        self.stmts.append(cgen.Statement(st_str))

    def add_line(self, st_str):
        self.stmts.append(cgen.Line(st_str))

class ModuleBlock(GenericBlock):
    def to_block(self):
        o = Module()

        for d in self.decls:
            o.append(d)

        for s in self.stmts:
            if isinstance(s, GenericBlock):
                vs = s.to_block()
                o.append(vs)
            else:
                o.append(s)

        return o

class FunctionBlock(GenericBlock):
    def __init__(self):
        self.args = []
        super(FunctionBlock, self).__init__()

    def to_block(self):
        assert False

        o = Module()

        for d in self.decls:
            o.append(d)

        for s in self.stmts:
            if isinstance(s, GenericBlock):
                vs = s.to_block()
                o.append(vs)
            else:
                o.append(s)

        return o
        
       

def BlankLine():
    return cgen.Line("")

def default_tid_bid_initializer():
    out = [Initializer(Value("unsigned", "tid"), "TID_1D"),
           Initializer(Value("unsigned", "nthreads"), "TOTAL_THREADS_1D"),
           BlankLine()]

    return out

# need to merge with pipe tree builder in iteroutliner
class PipeKernelAnalysis(gg.ast.walkers.ASTPreOrderWalker):
    def __init__(self):
        self.kernels = set()

    def generic_node_visitor(self, node):
        if isinstance(node, gg.ast.Iterate) or isinstance(node, gg.ast.Invoke):
            self.kernels.add(node.kernel)
    
        return True
    
    @staticmethod
    def get_kernels(node):
        x = PipeKernelAnalysis()
        x.visit(node)
        return x.kernels


class CUDAPreGen(gg.ast.walkers.ASTWalker):
    def __init__(self, astinfo):
        self.astinfo = astinfo

    def visit_Kernel(self, node):
        self.kernel = node
        super(CUDAPreGen, self).visit_Kernel(node)
        self.kernel = None

    def visit_ForAll(self, node):
        if node.nesting_level == 1:
            #TODO:URGENT
            if "MULT" in node.props:
                node.ndxvar = gg.ndxtrans.StretchIndex(node.ndxvar.iterator)
                node.ndxvar.mult = node.props['MULT']
            else:
                node.ndxvar.offset = "tid"
                node.ndxvar.increment = "nthreads"
        else:
            pass

        # this is really a backend-independent thing
        if node.has_anno('uniform') and node.anno.uniform.uniform:            
            if self.kernel.contains_exclusive or self.kernel.barrier_level == 0:
                #TODO: this is conservative -- it is the for_loop that needs to contain exclusive/globalbarrier for nthreads to apply

                #node.ndxvar.iterator = gg.ndxtrans.UniformIterator(node.ndxvar.iterator, "nthreads")
                node.ndxvar = gg.ndxtrans.UniformIndex(node.ndxvar, "nthreads")
            else:
                node.ndxvar = gg.ndxtrans.UniformIndex(node.ndxvar, "blockDim.x")

        if hasattr(node, 'distribution') and node.distribution == "block":
            if self.compiler.options.retry_backoff:
                node.ndxvar = gg.ndxtrans.BlockedDistribution(node.ndxvar, "tid", "nthreads")
                

class GenCommon(gg.ast.walkers.ASTWalker):
    pass

class CUDAGen(gg.ast.walkers.ASTWalker):
    kernels = None
    blocks = None
    cur_block = None

    def __init__(self, astinfo):
        self.astinfo = astinfo
        self.kernels = {}
        self.blocks = Stack()
        self.loops = Stack()
        
        self.pipe_ctx = None
        self.kernel = None

    def set_options(self, compiler, options):
        self.compiler = compiler
        self.options = options
        self.WL_TYPE = WL_TYPES[options.worklist_type]
        self.PIPE_TYPE = PIPE_TYPE_TEMPLATE % (self.WL_TYPE,)
        self.GRAPH_TYPE = GRAPH_TYPES[options.graph_type]  
        self.AOL_TYPE = AOL_TYPES['basic']

    @property
    def cur_block(self):
        return self.blocks.top
        self.cur_block = None

    def visit_Atomic(self, node):
        self.blocks.push(GenericBlock())
        self.visit(node.stmts)
        self.visit(node.fail_stmts)
        c = self.blocks.pop()

        lsym = node.symtab.lookup(node.lock)

        release_stmt = cgen.Statement(node.lock + ".release(" + node.lockndx + ")")
        
        ct_stmts = c.stmts[0]
        ct_stmts.append(release_stmt)
        
        if len(node.fail_stmts.stmts): 
            cf_stmts = c.stmts[1]
        else:
            cf_stmts = None
            
        if not cf_stmts:
            if True: # workaround CUDA 7.x and 8.x bugs
                # this is around 0.23x slower than 6.0 (tested on mst-wl-test)
                setup_stmts = [cgen.Line("#if __CUDACC_VER_MAJOR__ >= 7"),
                               cgen.Statement("volatile bool done_ = false"),
                               cgen.Line("#else"),
                               cgen.Statement("bool done_ = false"),
                               cgen.Line("#endif")]
            else:
                setup_stmts = [cgen.Statement("bool done_ = false")]

            if lsym.ty == PARAM_LOCKARRAY_TICKET:
                setup_stmts += [cgen.Statement("int _ticket = (%s).reserve(%s)" % (node.lock, node.lockndx))]
                acq_or_fail = node.lock + ".acquire_or_fail(" + node.lockndx + ", _ticket)"
            else:
                acq_or_fail = node.lock + ".acquire_or_fail(" + node.lockndx + ")"

            ct_stmts.append(cgen.Statement("done_ = true"))

            body = [cgen.If(acq_or_fail, ct_stmts, cf_stmts)]

            self.cur_block.stmts.append(Block(setup_stmts + [cgen.While("!done_", Block(body))]))
        else:
            assert lsym.ty != PARAM_LOCKARRAY_TICKET, "Ticket lock '%s' cannot be used for Atomic blocks with Else clause" % (lsym.name,)
            self.cur_block.stmts.append(cgen.If(node.lock + ".acquire_or_fail(" + node.lockndx + ")", 
                                                ct_stmts, cf_stmts))

    def _appropriate_exit(self): # from logical thread
        if len(self.loops) == 0:
            return cgen.Statement("return")
        else:
            #TODO: this assumes internal ForAll loops are serialized!

            if isinstance(self.loops.top, gg.ast.ForAll):
                return cgen.Statement("continue")

            for l in reversed(self.loops):
                if isinstance(l, gg.ast.ForAll):
                    l._exit_label = True
                    return cgen.Statement("goto next_%s" % (l.loop_id,))

            return cgen.Statement("return")

    def visit_Retry(self, node):
        if not isinstance(node, gg.ast.Respawn):
            self.cur_block.stmts.append(self._appropriate_exit())

    def visit_Exclusive(self, node):
        def gen_stmts(n, fn, fn_it):
            out = []
            for obj, items in n:
                for tli in items:
                    if isinstance(tli, gg.ast.ExclusiveArrayIterator):
                        out.append(fn_it(tli))
                    else:
                        n, array = tli
                        out.append(fn((obj, n, array)))
            return out

        self.blocks.push(GenericBlock())
        self.visit(node.stmts)
        self.visit(node.fail_stmts)
        c = self.blocks.pop()

        block, f_block = c.stmts[0], c.stmts[1]
        
        assert len(node.to_lock) == 1, "Multiple objects not yet supported in Exclusive"

        # TODO: multiple exclusive statements 
        # in the same kernel on different objects
        # TODO: exclusive statement on multiple objects

        x = []
        x += gen_stmts(node.to_lock, 
                       lambda x: cgen.Statement("_ex.mark_p1(%s, %s, tid)" % (x[1], x[2])),
                       lambda y: cgen.Statement("_ex.mark_p1_iterator(%s, %s, %s, %s, tid)" % (y.start,
                                                                                               y.end,
                                                                                               y.step,
                                                                                               y.array)))
        x.append(cgen.Statement("gb.Sync()"))
        x += gen_stmts(node.to_lock, 
                       lambda x: cgen.Statement("_ex.mark_p2(%s, %s, tid)" % (x[1], x[2])),
                       lambda y: cgen.Statement("_ex.mark_p2_iterator(%s, %s, %s, %s, tid)" % (y.start,
                                                                                               y.end,
                                                                                               y.step,
                                                                                               y.array)))
        
        x.append(cgen.Statement("gb.Sync()"))
        x.append(cgen.Statement('int _x = 1'))

        x += gen_stmts(node.to_lock, 
                       lambda x: cgen.Statement("_x &= _ex.owns(%s, %s, tid)" % (x[1], x[2])),
                       lambda y: cgen.Statement("_x &= _ex.owns_iterator(%s, %s, %s, %s, tid)" % (y.start,
                                                                                                  y.end,
                                                                                                  y.step,
                                                                                                  y.array)))
        
        x.append(cgen.If('_x', block, f_block))

        # no releases required
        self.cur_block.stmts.append(Block(x))
        
    def _visit_CDecl(self, node):
        #TODO: data dependences between declarations
        # this was done to handle declarations that contained a mix of initialized and non-initialized
        dont_move = node.dont_move or any([x[2] for x in node.decls])

        for (t, v, i) in node.decls:
            if not dont_move:
                if i:
                    s = cgen.Statement("%s %s %s" % (t, v, i))
                else:
                    s = cgen.Statement("%s %s" % (t, v))
                
                self.cur_block.decls.append(s)
            else:
                self.cur_block.stmts.append(cgen.Statement("%s %s %s" % (t, v, i)))

    def visit_CBlock(self, node):
        if node.decl:
            self._visit_CDecl(node)
            return
        else:
            x = self.cur_block.stmts

        if node._scope != "all":
            if node._scope == "gpu" and self.kernel.host:
                return
            
            if node._scope == "cpu" and not self.kernel.host:
                return

        for s in node.stmts:
            # this make it {; which is okay for now
            if isinstance(s, str):
                if s != "":
                    x.append(cgen.Statement(s))
                else:
                    x.append(cgen.Line())
            else:
                # s is a generable
                x.append(s)


    def visit_If(self, node):
        self.blocks.push(GenericBlock())
        self.visit(node.true_stmts)
        self.visit(node.false_stmts)
        c = self.blocks.pop()

        ct_stmts = c.stmts[0]
        if len(node.false_stmts.stmts): 
            cf_stmts = c.stmts[1]
        else:
            cf_stmts = None

        self.cur_block.stmts.append(cgen.If(node.cond, 
                                            ct_stmts, cf_stmts))

    def visit_CFor(self, node):
        self.blocks.push(GenericBlock())
        self.loops.push(node)
        self.visit(node.stmts)

        c = self.blocks.pop()

        out = []
        init = []
        for i in node.init:
            if isinstance(i, gg.ast.CDecl):
                if len(init):
                    init += ["%s %s" % (ii[1], ii[2]) for ii in i.decls]
                else:
                    init += ["%s %s %s" % ("" if nii > 0 else ii[0], ii[1], ii[2]) for nii, ii in enumerate(i.decls)]
            else:
                init.append(i)

        out += [cgen.For(", ".join(init),
                         node.cond,
                         ", ".join(node.update),
                         c.stmts[0])]
        
        self.cur_block.stmts += out
        self.loops.pop()

    def visit_While(self, node):
        self.blocks.push(GenericBlock())
        self.loops.push(node)
        self.visit(node.stmts)
        c = self.blocks.pop()

        out = []
        out += [cgen.While(node.cond, c.stmts[0])]
        
        self.cur_block.stmts += out
        self.loops.pop()

    def visit_DoWhile(self, node):
        self.blocks.push(GenericBlock())
        self.loops.push(node)
        self.visit(node.stmts)
        c = self.blocks.pop()

        out = []
        out += [cgen.DoWhile(node.cond, c.stmts[0])]
        
        self.cur_block.stmts += out
        self.loops.pop()

    def _visit_loop(self, node):
        self.blocks.push(GenericBlock())
        self.loops.push(node)

        self.visit(node.stmts)

        c = self.blocks.pop()

        # the CUDA compiler really wants loops to start from 0 
        # 10% improvement on bfs-topo-USA

        nv = node.ndxvar
        list(map(self.cur_block.decls.append, nv.decls()))

        if hasattr(nv, "pre_body_code"):
            z = nv.pre_body_code()
            z.reverse()
            for x in z:
                c.stmts.insert(0, x)

        if hasattr(node, '_exit_label') and node._exit_label == True:
            exit_part = [cgen.Line("next_%s:" % node.loop_id), 
                         cgen.Statement("")]
        else:
            exit_part = []

        out = []
        out += nv.pre_loop_code()
        out += [cgen.For(nv.loop_init(), 
                         nv.loop_cond(), 
                         nv.loop_update(),         
                         Block(c.stmts[0].contents + exit_part))]
        
        self.cur_block.stmts += out
        self.loops.pop()
        
    def visit_For(self, node):
        self._visit_loop(node)

    def visit_ForAll(self, node):
        self._visit_loop(node)

    def visit_Assign(self, node):
        self.blocks.push(GenericBlock())
        self.visit(node.rhs)
        c = self.blocks.pop()
        
        assert len(c.decls) == 0 # TODO
        assert len(c.stmts) == 1

        self.cur_block.add_stmt("%s = %s" % (node.lhs, c.stmts[0]))

    def visit_CExpr(self, node):
        self.cur_block.stmts.append(node.expr) #TODO: not ideal ...

    def _get_call_tbsize(self, kernel, invocation, default = None):
        # TODO: allow invocation site to overrride?
        k = self.unit.kernels[kernel]
        if k.has_anno("call_config") and isinstance(k.anno.call_config.block, (ShrinkableBlockTy, FixedBlockTy)):
            return k.anno.call_config.block.var

        return default

    def visit_MethodInvocation(self, node):

        if node.obj_type == "Worklist":
            if node.method == "push":
                self.cur_block.add_stmt("(%s).push(%s)" % (node.obj, node.args[0]))
            elif node.method == "push_prio":
                self.cur_block.add_stmt("(%s).push(%s, %s)" % (node.obj, node.args[0], node.args[1]))
            elif node.method == "push_coop":
                self.cur_block.add_stmt("(%s).push_1item<BlockScan>(int(%s), (int) %s, __kernel_tb_size)" % (node.obj, node.args[0], node.args[1]))            
            elif node.method == "pop":
                #self.cur_block.decls.append(cgen.Statement("int %s" % (node.args[1])))
                if not USE_POP_ID_LEN:
                    self.cur_block.stmts.append(cgen.Assign(node.args[0], "(%s).pop_id(%s, %s)" % (node.obj, node.args[1], node.args[2])))
                else:
                    self.cur_block.stmts.append(cgen.Assign(node.args[0], "(%s).pop_id_len(%s, %s, %s)" % (node.obj, node.args[1], 
                                                                                                       node.args[1] + "_end",
                                                                                                       node.args[2])))
            elif node.method == "print_size":
                assert self.pipe_ctx, "Pipe context must be set for worklist print_size"
                self.cur_block.add_stmt('printf("%%d: worklist size is: %%u\\n", %s, (%s).in_wl().nitems())' % (node.args[0], self.pipe_ctx,))
            elif node.method == "display_items":
                assert self.pipe_ctx, "Pipe context must be set for worklist display_items"
                self.cur_block.add_stmt('(%s).in_wl().display_items()' % (self.pipe_ctx,))
            elif node.method == "push_id":
                self.cur_block.add_stmt("(%s).push_id(%s, %s)" % (node.obj, node.args[0], node.args[1]))
            elif node.method == "push_range":
                self.cur_block.add_stmt("(%s).push_range(%s)" % (node.obj, node.args[0]))
            elif node.method == "do_push":
                self.cur_block.add_stmt("(%s).do_push(%s, %s, %s)" % (node.obj, node.args[0], node.args[1], node.args[2]))
            elif node.method == "setup_push_warp_one":
                self.cur_block.add_stmt("(%s).setup_push_warp_one()" % (node.obj))
            else:
                assert False, "Unsupported worklist method: %s" % (node.method,)
        elif isinstance(node.obj, gg.ast.HierarchicalBarrier):
            if node.method == "sync":
                if node.obj.level == 1:
                    self.cur_block.add_stmt("__syncthreads()")
                elif node.obj.level == 0:
                    self.cur_block.add_stmt("gb.Sync()")
                else:
                    assert node.obj.level < 2, "Can't compile barriers at level %d (max: 1)" % (node.obj.level,)
            elif node.method == "setup":
                fn = node.args[0]
                thr = self._get_call_tbsize(fn, None, default="threads.x")
                
                self.cur_block.stmts.append(cgen.Statement("static const size_t %s_residency = maximum_residency(%s, %s, 0)" % (fn, fn, thr)))
                self.cur_block.stmts.append(cgen.Statement("static const size_t %s_blocks = GG_MIN(blocks.x, ggc_get_nSM() * %s_residency)" % (fn, fn)))

                self.cur_block.decls.append(cgen.Statement("static GlobalBarrierLifetime %s_barrier" % (fn,)))
                self.cur_block.decls.append(cgen.Statement("static bool %s_barrier_inited" % (fn,)))
                
                self.cur_block.add_stmt("if(!%s_barrier_inited) { %s_barrier.Setup(%s_blocks); %s_barrier_inited = true;}" % (fn, fn, fn, fn))
            else:
                assert False, "Unknown barrier method: %s" % (node.method,)
        elif node.obj_type == "Exclusive":
            if node.method == "setup":
                self.cur_block.decls.append(cgen.Statement("ExclusiveLocks %s_ex_locks(%s)" % (node.args[1], node.args[0])))
            else:
                assert False, "Unknown barrier method: %s" % (node.method,)
        elif node.obj_type == "AppendOnlyList":
            if node.method == "display":
                self.cur_block.add_stmt("%s.display_items()" % (node.obj,))
            elif node.method == "push":
                self.cur_block.add_stmt("%s.push(%s)" % (node.obj, node.args[0]))
            elif node.method == "pop":
                self.cur_block.stmts.append(cgen.Assign(node.args[0], "(%s).pop_id(%s, %s)" % (node.obj, node.args[1], node.args[2])))
            elif node.method == "push_coop":
                self.cur_block.add_stmt("(%s).push_1item<BlockScan>(int(%s), (int) %s, TB_SIZE)" % (node.obj, node.args[0], node.args[1]))
            elif node.method == "setup_push_warp_one":
                self.cur_block.add_stmt("(%s).setup_push_warp_one()" % (node.obj))
            elif node.method == "setup_push_thread":
                self.cur_block.add_stmt("(%s).setup_push_thread(%s)" % (node.obj, node.args[0]))
            elif node.method == "do_push":
                self.cur_block.add_stmt("(%s).do_push(%s, %s, %s)" % (node.obj, node.args[0], node.args[1], node.args[2]))
            else:
                assert False, "Unknown list method: %s" % (node.method,)
        elif node.obj_type == "RV":
            if node.method == "return":
                self.cur_block.add_stmt("%s.return_(%s)" % (node.obj, node.args[0]))
            elif node.method == "do_return":
                self.cur_block.add_stmt("%s.do_return(%s)" % (node.obj, node.args[0]))                
            else:
                assert False, "Unknown RV method: %s" % (node.method,)
        elif node.obj_type == "Graph":
            if node.method == "valid_node":
                self.cur_block.add_stmt("%s.valid_node(%s)" % (node.obj, node.args[0]))
            else:
                assert False, "Unknown Graph method: %s" % (node.method,)
        else:
            assert False, "Unknown method invocation: %s.%s" % (node.obj_type, node.method,)

    def _generate_launch_bounds(self, node, func_body):
        #TODO: check that this is a global function

        if not (hasattr(node.anno, 'cuda') and hasattr(node.anno.cuda, "launch_bounds")):
            return func_body

        bounds = list(node.anno.cuda.launch_bounds.bounds.values())

        if len(bounds) == 1:
            return CudaLaunchBounds(bounds[0][0], func_body, bounds[0][1])
        else:
            #TODO: setup these variables

            mb = "%s_MIN_BLOCKS" % (node.name,) if any([x[1] is not None for x in bounds]) else None
            return CudaLaunchBounds("%s_MAX_THREADS" % (node.name,), func_body, mb)

    def expand_kernel_params(self, node):
        out = []

        lightened = node.name[-6:] == "_light" and "lighten-wl" in self.compiler.options.hacks and node.device

        for (t, p) in node.anno.kernel_params.params:
            if t == PARAM_WL:
                ty = self.WL_TYPE
                
                if lightened:
                    out.append(Value(ty + "Light", "in_" + p))
                    out.append(Value(ty + "Light", "out_" + p))
                else:
                    out.append(Value(ty, "in_" + p))
                    out.append(Value(ty, "out_" + p))

                if node.contains_retry:
                    out.append(Value(ty, "re_" + p))
            elif t == PARAM_EXCLUSIVE_LOCKS:
                out.append(Value('ExclusiveLocks', p))
            elif t == PARAM_GLOBAL_BARRIER:
                out.append(Value('GlobalBarrier', p))
            elif t == PARAM_RETVAL:
                # TODO:
                assert "ALL" not in node.call_contexts
                out.append(Value('Any', p))
            else:
                assert False, t

        return out

    def visit_Kernel(self, node):
        self.kernel = node
        self.kernel_block = FunctionBlock()

        self.blocks.push(GenericBlock())
        self.visit(node.stmts)
        c = self.blocks.pop()

        blk_stmts = []
        if node.name == "gg_main":
            blk_stmts += [cgen.Statement("dim3 blocks, threads"), 
                          cgen.Statement("kernel_sizing(gg, blocks, threads)")]
            
            if self.compiler.options.instrument_mode == 'load':
                blk_stmts.append(cgen.Statement('instr_load_uniqid()'))

            if 'kstate' in self.compiler.options.instrument:
                mode = 1 if 'save' == self.compiler.options.instrument_mode else 0
                blk_stmts.append(cgen.Statement('struct instr_trace *_instr_trace = instr_trace_file("gg_main", %d)' % (mode,)))

        elif not node.host:
            #TODO: remove these for outlined with dev kernels
            blk_stmts = default_tid_bid_initializer()

            assert node.has_anno("call_config") or node.device, node.name

            if node.has_anno("call_config") and isinstance(node.anno.call_config.block, FixedBlockTy):
                blk_stmts.append(cgen.Statement("const unsigned __kernel_tb_size = " + node.anno.call_config.block.var))
            else:
                blk_stmts.append(cgen.Statement("const unsigned __kernel_tb_size = TB_SIZE")) # TODO

            if self.options.use_worklist_slots and not node.device and node.contains_wl:
                blk_stmts += [If("tid == 0", cgen.Statement("in_wl.reset_next_slot()")), BlankLine()]


        for decl in node.anno.entry_exit.decls:
            ds = node.anno.entry_exit.decls[decl]
            if not isinstance(ds, list): ds = [ds]

            for l in ds:
                blk_stmts.append(cgen.Statement(l))

        for stmt in node.anno.entry_exit.at_entry:
            blk_stmts.append(cgen.Statement(stmt))

        blk_stmts += c.stmts[0].contents

        for stmt in node.anno.entry_exit.at_exit:
            blk_stmts.append(cgen.Statement(stmt))

        args = []
        for (t, p) in node.args + self.kernel_block.args:
            if t == PARAM_WL:
                if node.device:
                    args.append(Value(self.WL_TYPE + "&", p))
                else:
                    args.append(Value(self.WL_TYPE, p))
            elif t == PARAM_APPEND_ONLY_LIST:
                args.append(Value(self.AOL_TYPE, p))
            elif t == PARAM_APPEND_ONLY_LIST_REF:
                args.append(Value(self.AOL_TYPE + "&", p))
            elif t == PARAM_PIPE:
                args.append(Value(self.PIPE_TYPE, p))
            elif t == PARAM_PIPE_REF:
                args.append(Value(self.PIPE_TYPE + "&", p))
            elif t == PARAM_LOCK:
                assert False, "PARAM_LOCK not yet implemented"
            elif t == PARAM_LOCKARRAY:
                args.append(Value('LockArray', p))
            elif t == PARAM_GRAPH:
                args.append(Value(self.GRAPH_TYPE, p))
            elif t == PARAM_GRAPH_REF:
                args.append(Value(self.GRAPH_TYPE + "&", p))
            elif t == PARAM_LOCKARRAY_TICKET:
                args.append(Value('LockArrayTicket', p))                
            else:
                assert "+" not in t, "Unrecognized type: '%s'" % (t,)
                args.append(Value(t, p))

        self.kernels[node.name] = node

        args += self.expand_kernel_params(node)
        if node.has_anno('filter') and node.anno.filter.filtered:
            args += [Value('unsigned char *', '_filter')]
        
        out = self.cur_block

        if node._emit:
            if node.host:
                out.stmts.append(FunctionBody(FunctionDeclaration(
                            Value(node.ret_type, node.name),
                            arg_decls=args), Block(blk_stmts)))
            else:
                if node.device:
                    out.stmts.append(FunctionBody(CudaDevice(FunctionDeclaration(
                                    Value(node.ret_type, node.name),
                                    arg_decls=args)), Block(blk_stmts)))

                else:
                    out.stmts.append(FunctionBody(self._generate_launch_bounds(node, CudaGlobal(FunctionDeclaration(
                                        Value("void", node.name),
                                        arg_decls=args))), Block(blk_stmts)))
        
        self.kernel_block = None
        self.kernel = None

    def visit_ReturnFromParallelFor(self, node):
        #self.cur_block.stmts.append(cgen.Statement("ret_val.return_(1)"))
        if not hasattr(node, "_in_np") or not node._in_np:
            self.cur_block.stmts.append(self._appropriate_exit())

    def visit_Invoke(self, node):
        self._compile_invocation(node, node.kernel, node.args, self.cur_block.stmts, node.alt, node._noadvance)
        
    def _compile_pipe_invocation(self, node, kernel, out):
        if node.has_anno("closure"):
            args = [x.init for x in node.anno.closure.items("cpu", "cpu")]

            # TODO: fix this hack

            try:
                pos = args.index("pipe")
            except ValueError:
                pos = -1

            if pos >= 0:
                args[pos] = self.pipe_ctx
        else:
            args = node._call + [self.pipe_ctx]

        args = list(args)
        for i, a in enumerate(args):
            if "Shared<" in a:
                args[i] = a[7:-1]
 
        out.append(cgen.Statement("%s_wrapper(%s)" % (kernel, ",".join(args))))

    def _decode_filter_size(self, k, invc, args):
        assert k.has_anno("filter")

        if k.anno.filter.size == 'nodes':
            for i, (t, v) in enumerate(k.args):
                # HACK This picks the first graph

                if t == '+Graph+':
                    return "(%s).nnodes" % (args[i],)
        elif k.anno.filter.size == 'wlsize':
            assert self.pipe_ctx, "Need pipe for filter with wlsize"
            if k.outer_forall_arg_idx == -1: # uses default worklist
                return '%s.in_wl().nitems()' % (self.pipe_ctx,)
            else:
                return '(%s).nitems()' % (args[k.outer_forall_arg_idx]) # TODO: only AOL?
        elif k.anno.filter.size == 'range':
            for i, (t, v) in enumerate(k.args):
                # HACK This uses nedges only because the default bmks uses nedges

                if t == '+Graph+':
                    return "(%s).nedges" % (args[i],)
        else:
            assert False, k.anno.filter_size

    def _pre_call_instr(self, invc, args):
        if not self.kernel.host:
            return []

        kernel = invc.kernel
        k = self.unit.kernels[kernel]
        imode = self.compiler.options.instrument_mode
        out = []

        cntvar = None
        if 'kstate' in self.compiler.options.instrument:
            cntvar = "_%s_count" % (kernel,)
            if 'save' == imode:
                x = cuda_instr.savestates(k, invc, args, cntvar)
            elif 'load' == imode:
                x = cuda_instr.loadstates(k, invc, args, cntvar)

            if len(x) > 0: 
                out += x
            else:
                cntvar = None

        if "wlcontents" in self.compiler.options.instrument and self.pipe_ctx and k.outer_forall_is_wl:
            cntvar = "_%s_count" % (kernel,)
            if k.outer_forall_arg_idx == -1: # uses default worklist
                out.append(cgen.Statement('%s.in_wl().%s("%s", %s)' % (self.pipe_ctx, 
                                                                       imode, 
                                                                       kernel, cntvar)))
            else:
                out.append(cgen.Statement('(%s).%s("%s", %s)' % (args[k.outer_forall_arg_idx], 
                                                                       imode, 
                                                                       kernel, cntvar)))

        if "wlsort" in self.compiler.options.instrument and self.pipe_ctx and k.outer_forall_is_wl:
            # no point in sorting "after" saving?
            assert imode == 'load' or imode is None, imode

            if k.outer_forall_arg_idx == -1: # uses default worklist
                out.append(cgen.Statement('%s.in_wl().sort()' % (self.pipe_ctx,)))
            else:
                out.append(cgen.Statement('(%s).sort()' % (args[k.outer_forall_arg_idx])))

        if "savefilter" in self.compiler.options.instrument and k.has_anno("filter"):
            assert imode == 'load', "Savefilter only supports imode == 'load'"
            vname = '_filter_%s' % (k.name)
            sz = self._decode_filter_size(k, invc, args)
            out.append(cgen.Statement('Shared<unsigned char> %s(%s)' % (vname,sz)))
            out.append(cgen.Statement('%s.zero_gpu()' %  (vname,)))

        if cntvar:
            out.append(cgen.Statement("%s++" % (cntvar,)))
               
        return out

    def _post_cuda_call(self, k):
        out = []

        if "savefilter" in self.compiler.options.instrument and k.has_anno("filter"):
            assert self.compiler.options.instrument_mode == 'load', "Savefilter only supports imode == 'load'"
            out += cuda_instr.filter(k, len(k.args), "_%s_count" % (k.name,))

        if "wlatomicdensity" in self.compiler.options.instrument and k.writes_wl:
            out.append(cgen.Line("#ifdef ATOMIC_DENSITY"))
            out.append(cgen.Statement('print_atomic_density_2("%s", _%s_count, "out", %s.out_wl())' % (k.name,
                                                                                                       k.name, self.pipe_ctx,)))

            if k.contains_retry:
                out.append(cgen.Statement('print_atomic_density_2("%s", _%s_count, "re", %s.re_wl())' % (k.name,
                                                                                                         k.name, self.pipe_ctx,)))

            out.append(cgen.Line("#endif"))

        return out
        
    def _compile_invocation(self, invc, kernel, args, out, alt, _noadvance = False):
        assert kernel in self.kernels, "Kernel '%s' not found while visiting '%s'" % (kernel,self.kernel.name)
        k = self.kernels[kernel]

        oargs = args
        args = list(args) 

        lighten_mode = ("lighten-wl" in self.compiler.options.hacks) and not self.kernel.host and k.device and not k.contains_retry
        lighten_mode = lighten_mode and k.name + "_light" in self.kernels

        if k.contains_wl:
            assert self.pipe_ctx is not None, "Need a pipe context when compiling call to %s in %s" % (k.name, self.kernel.name)
            if lighten_mode:
                args += ["%s_light.wl[_light_index]" % (self.pipe_ctx,), 
                         "%s_light.wl[_light_index ^ 1]" % (self.pipe_ctx,)]
            else:
                args += ["%s.in_wl()" % (self.pipe_ctx,), 
                         "%s.out_wl()" % (self.pipe_ctx,)]

            if k.contains_retry:
                args += ["%s.re_wl()" % (self.pipe_ctx,)]
        
        if invc.has_anno("cuda_launch_config"):
            # TODO: fix this up for oitergb [i.e. disable kernel oitergb for such kernels] ...
            blocks = invc.anno.cuda_launch_config.blocks
            assert invc.anno.cuda_launch_config.threads == "threads"
        else:
            blocks = "blocks"

        if k.contains_exclusive:
            # TODO: multiple exclusive locks 
            args.append("%s_ex_locks" % (kernel,))

        if k.contains_barrier and k.barrier_level == 0:
            # TODO: will need work when variants are created
            blocks = "%s_blocks" % (kernel,)
            if k.device:
                args.append('gb')
            else:
                args.append('%s_barrier' % (kernel,))
           
        if k.contains_rfpf:
            if self.kernel.host:
                #TODO: make retval a parameter
                #args.append("retval.gpu_wr_ptr()")
                args.append("_rv")

                out.append(cgen.Statement("Shared<int> retval = Shared<int>(1)")) # TODO lift this out of loop?
                out.append(cgen.Statement("Any _rv"))
                out.append(cgen.Statement("*(retval.cpu_wr_ptr()) = 0"))
                out.append(cgen.Statement("_rv.rv = retval.gpu_wr_ptr()"))
            else:
                out.append(cgen.Statement("Any _rv"))
                args.append('_rv')
                out.append(cgen.Statement("*retval = 0"))
                out.append(cgen.Statement('_rv.rv = retval'));


        if k.has_anno("filter") and k.anno.filter.filtered:
            args.append('_filter_%s.gpu_wr_ptr()' % (k.name,))

        if not self.kernel.host:
            for i, x in enumerate(args):
                if ".gpu_wr_ptr()" in  x:
                    args[i] = x[:x.rindex(".gpu_wr_ptr()")]
                elif ".gpu_rd_ptr()" in  x:
                    args[i] = x[:x.rindex(".gpu_rd_ptr()")]

        args = ", ".join(args)

        call_stmt = []

        if k.contains_wl and self.kernel.host:            
            call_stmt.append(cgen.Statement("%s.out_wl().will_write()" % (self.pipe_ctx,)))
            if k.contains_retry:
                call_stmt.append(cgen.Statement("%s.re_wl().will_write()" % (self.pipe_ctx,)))

                # not (True in k.retry_merges) is a very blunt!
                if self.compiler.options.retry_backoff and k.contains_exclusive and not (True in k.retry_merges):
                    call_stmt.append(cgen.Statement("size_t _%s_retry = %s" % (blocks, blocks,)))
                    old_blocks = blocks
                    blocks = "_%s_retry" % (blocks,)
                    # because we know adjacent entries may conflict with high probability
                    # requires that ForLoop() be blocked...
                    call_stmt.append(cgen.Statement("int _nitems = (%s).in_wl().nitems() / %s" % (self.pipe_ctx, self.compiler.options.backoff_blocking_factor))) 
                    call_stmt.append(cgen.If("%s * threads.x > _nitems" % (blocks,), 
                                             cgen.Block([cgen.Statement("%s = (_nitems + threads.x - 1) / threads.x" % (blocks,)),
                                                         cgen.Statement("assert(%s <= %s)" % (blocks, old_blocks)),
                                                         cgen.If("(%s == 0)" % (blocks), cgen.Statement("%s = 1" % (blocks,))),
                                                         ]
                                                        )))

        if alt:
            call_stmt.append(cgen.If(alt[0], 
                                     cgen.Statement("%s <<<%s, threads>>>(%s)" % (alt[1], blocks, args)),
                                     cgen.Statement("%s <<<%s, threads>>>(%s)" % (kernel, blocks, args))
                               ))
        else:
            if k.device:
                # for now, otherwise it should be in _dev itself

                if k.contains_rfpf: # or any other global update ...
                    call_stmt.append(cgen.Statement('gb.Sync()'))

                if k.contains_wl and self.options.use_worklist_slots:
                    if lighten_mode:
                        call_stmt.append(If("tid == 0", cgen.Statement("%s_light.wl[_light_index].reset_next_slot()" % (self.pipe_ctx))))
                    else:
                        call_stmt.append(If("tid == 0", cgen.Statement("%s.in_wl().reset_next_slot()" % (self.pipe_ctx,))))

                if lighten_mode:
                    call_stmt.append(cgen.Statement("%s_light (%s)" % (kernel, args)))
                else:
                    call_stmt.append(cgen.Statement("%s (%s)" % (kernel, args)))

                if k.contains_rfpf:
                    call_stmt.append(cgen.Statement('_rv.local = *retval'))

            else:
                call_stmt += self._pre_call_instr(invc, oargs)
                thr = self._get_call_tbsize(kernel, invc, "threads")
                call_stmt.append(cgen.Statement("%s <<<%s, %s>>>(%s)" % (kernel, blocks, thr, args)))


        call_stmt += self._post_cuda_call(k)

        if k.contains_retry:
            if self.options.use_worklist_slots:
                call_stmt.append(cgen.Statement("%s.in_wl().swap_slots()" % (self.pipe_ctx,)))              

            if not self.kernel.host:
                if not k.device:
                    call_stmt.append(cgen.Statement("cudaDeviceSynchronize()"))
                else:
                    call_stmt.append(cgen.Statement("gb.Sync()"))

            if self.options.use_worklist_slots:
                call_stmt.append(cgen.Statement("%s.retry2()" % (self.pipe_ctx,)))
            else:
                call_stmt.append(cgen.Statement("%s.retry()" % (self.pipe_ctx,)))

            # TODO: catch this as an error early on!
            assert len(k.retry_merges) == 1, "Retry statements within same kernel have multiple merge values"

            if True in k.retry_merges:
                out.append(Block(call_stmt))
            else:
                cond = self._wl_loop_cond(self.pipe_ctx, invc)
                call_stmt = self._wl_loop_entry(invc) + call_stmt
                out.append(cgen.While(cond, Block(call_stmt)))
                out += self._wl_loop_post(invc, False) # retry never creates a pipe

        else:
            for s in call_stmt:
                out.append(s)

        # there must always be a reset_next_slot() before a swap_slots
        
        # there must always be an advance2/retry2 between swap_slots
        # for the same list

        if k.writes_wl and not _noadvance:
            if self.options.use_worklist_slots and not k.contains_retry:
                if lighten_mode:
                    out.append(cgen.Statement("%s_light.wl[_light_index].swap_slots()" % (self.pipe_ctx,)))
                else:
                    out.append(cgen.Statement("%s.in_wl().swap_slots()" % (self.pipe_ctx,)))

            if not self.kernel.host:
                if k.device:
                    out.append(cgen.Statement("gb.Sync()"))
                else:
                    out.append(cgen.Statement("cudaDeviceSynchronize()"))

            if self.options.use_worklist_slots:
                out.append(cgen.Statement("%s.advance2()" % (self.pipe_ctx,)))
            else:
                out.append(cgen.Statement("%s.advance()" % (self.pipe_ctx,)))

            if lighten_mode: out.append(cgen.Statement("_light_index ^= 1"))

            if k.prio_wl:
                #TODO: see pop_prio
                out.append(cgen.Statement("%s.in_wl().sort_prio()" % (self.pipe_ctx,)))
        elif not k.writes_wl:
            if not self.kernel.host:
                if k.device:
                    out.append(cgen.Statement("gb.Sync()"))
                else:
                    out.append(cgen.Statement("cudaDeviceSynchronize()"))

    def _compile_any(self, node):
        assert node.condition == "ANY"
        
        def any_body(): # there? ;)
            self.blocks.push(GenericBlock())
            self.visit(node.stmts)
            c = self.blocks.pop()

            self.cur_block.decls.append(cgen.Initializer(cgen.Value("bool", "loopc"), "false"))

            out = Block([])
            cond = "loopc"
            if node.extra_cond:
                cond = cond + " %s %s" % node.extra_cond

            self._compile_invocation(node, node.kernel, node.kernel_args, out, None)

            if self.kernel.host:
                loopc = '*(retval.cpu_rd_ptr()) > 0'
                if 'kstate' in self.compiler.options.instrument and 'load' in self.compiler.options.instrument_mode:
                    instr_cond = self._wl_loop_cond(None, node)
                    if "instr_" in instr_cond:
                        out.append(cgen.Statement("bool _instr_iter = %s" % (instr_cond,)))
                        #out.append(cgen.Statement("assert(_instr_iter)"))
                        
                        if 'savefilter' in self.compiler.options.instrument:
                            # retval setting does not work when operator has been stripped out

                            loopc = '_instr_iter'
                    
                out.append(cgen.Statement("loopc = %s" % (loopc,)))
            else:
                k = self.kernels[node.kernel]
                # if k.device:
                #     out.append(cgen.Statement("gb.Sync()"))
                # else:
                #     out.append(cgen.Statement("cudaDeviceSynchronize()"))

                out.append(cgen.Statement("loopc = *retval > 0"))

            out.contents += c.stmts[0].contents

            if not self.kernel.host:
                if k.device and k.contains_rfpf: # or any other global update ...
                    out.append(cgen.Statement('gb.Sync()'))

            self.cur_block.stmts.append(cgen.DoWhile(cgen.Line(cond), out))
        
        outlined = hasattr(node, '_nn')
        inoutline = outlined and (hasattr(self.kernel.anno, "outline") and not self.kernel.anno.outline.wrapper and self.kernel.anno.outline.pipe_name == node._nn)

        if outlined and inoutline:
            cr = self._inherit_pipe_ctx("pipe")
            any_body()
            self._release_pipe_ctx(cr)
        else:
            if not outlined:
                any_body()
            else:
                out = []
                self._compile_pipe_invocation(node, node._nn, out)

                self.cur_block.stmts.append(out[0])

    def _visit_WorklistInitializer(self, node):
        self.cur_block.decls.append(cgen.Statement("%s %s" % (self.PIPE_TYPE, self.pipe_ctx)))

        self.cur_block.add_stmt("%s = %s(%s)" % (self.pipe_ctx, self.PIPE_TYPE, node.size))

        sz = None
        if isinstance(node, gg.ast.WorklistInitializerFromArray):
            self.cur_block.add_stmt("memcpy(%s.in_wl().wl, %s, (%s) * sizeof((%s)[0]))" % (self.pipe_ctx, node.array, node.array_size, node.array))
            sz = node.array_size
        elif isinstance(node, gg.ast.WorklistInitializer):
            for i, l in enumerate(node.initial):
                self.cur_block.add_stmt("%s.in_wl().wl[%d] = %d" % (self.pipe_ctx, i, l))

            sz = len(node.initial)

        if sz:
            self.cur_block.stmts.append(cgen.Statement("%s.in_wl().update_gpu(%s)" % (self.pipe_ctx, sz)))

    def _create_instr_vars(self):
        #TODO: this does not work if oiter/gb is also enabled!
        if "wlcontents" in self.compiler.options.instrument or "kstate" in self.compiler.options.instrument:
            #assert self.kernel.host, "Not in a host kernel!"

            for kk in self.unit.kernels:
                k = self.unit.kernels[kk]
                if k.has_anno("statesaver"):
                    self.cur_block.decls.append(cgen.Statement("unsigned _%s_count = 0" % (kk,)))

    def _create_or_get_pipe_ctx(self, wlinit, node, name = "pipe"):
        if not self.pipe_ctx:
            self.pipe_ctx = name
            assert wlinit is not None, "Must provide size for worklist"
            self._visit_WorklistInitializer(wlinit)
            
            return True

        return False

    def _inherit_pipe_ctx(self, name="pipe"):
        if not self.pipe_ctx:
            self.pipe_ctx = name
            return True
        else:
            assert self.pipe_ctx == name
            return False

    def _release_pipe_ctx(self, ret):
        if ret:
            self.pipe_ctx = None

    def _wl_loop_cond(self, ctx, pipe_node):
        if not self.kernel.host:
            return "%s.in_wl().nitems()" % (ctx,)

        if 'kstate' in self.compiler.options.instrument and 'load' in self.compiler.options.instrument_mode:
            cond = "instr_match_pipe_iterate(%s, %d, %d)" % ("_instr_trace", 
                                                             pipe_node.anno.pipe_anno.depth, 
                                                             pipe_node.anno.pipe_anno.index)
        else:
            cond = "%s.in_wl().nitems()" % (ctx,)

        return cond

    def _wl_loop_entry(self, pipe_node):
        out = []

        if not self.kernel.host:
            return out


        if not isinstance(pipe_node, gg.ast.Invoke):
            return out

        # this is only needed for Invoke-s with retry-able kernels
        if 'kstate' in self.compiler.options.instrument and 'save' in self.compiler.options.instrument_mode:
            out.append(cgen.Statement("instr_pipe_iterate(%s, %d, %d)" % ("_instr_trace", 
                                                                          pipe_node.anno.pipe_anno.depth, 
                                                                          pipe_node.anno.pipe_anno.index)))

        return out
            


    def _wl_loop_post(self, pipe_node, cr):
        # NOTE: pipe_node can be a Invoke for a Retry-able call!
        out = []
        if not self.kernel.host:
            return out

        # cr and "wlatomics" ...
        if cr and "wlatomics" in self.compiler.options.instrument:
            out.append(cgen.Line("#ifdef COUNT_ATOMICS"))
            out.append(cgen.Statement('printf("INSTR ATOMICS %%d %%d %%d\\n", get_atomic_count(%s.in_wl()), get_atomic_count(%s.out_wl()), get_atomic_count(%s.re_wl()))' % (self.pipe_ctx,
                                                                                                                                                                             self.pipe_ctx,
                                                                                                                                                                             self.pipe_ctx)))
            out.append(cgen.Line("#endif"))        

        # cr and "wlatomics" ...
        if cr and "wlatomicdensity" in self.compiler.options.instrument:
            # note this is over entire application and in, out, re are just names at this point
            out.append(cgen.Line("#ifdef ATOMIC_DENSITY"))
            out.append(cgen.Statement('print_atomic_density("in", %s.in_wl())' % (self.pipe_ctx,)))
            out.append(cgen.Statement('print_atomic_density("out", %s.out_wl())' % (self.pipe_ctx,)))
            out.append(cgen.Statement('print_atomic_density("re", %s.re_wl())' % (self.pipe_ctx,)))
            out.append(cgen.Line("#endif"))        

        if not isinstance(pipe_node, gg.ast.Invoke):
            return out


        if 'kstate' in self.compiler.options.instrument:
            if 'load' in self.compiler.options.instrument_mode:
                out.append(cgen.Statement("assert(instr_match_pipe_exit(%s, %d, %d))" % (("_instr_trace", 
                                                                                          pipe_node.anno.pipe_anno.depth, 
                                                                                          pipe_node.anno.pipe_anno.index))))
            else:
                # this is added by instrumentation pass
                out.append(cgen.Statement("instr_pipe_exit(%s, %d, %d)" % ("_instr_trace", 
                                                                           pipe_node.anno.pipe_anno.depth, 
                                                                           pipe_node.anno.pipe_anno.index)))



        return out

    def _compile_wl(self, node):
        # generate body of loop

        def wl_body():
            self.blocks.push(GenericBlock())
            self.visit(node.stmts)
            c = self.blocks.pop()

            out = Block([])
            self._compile_invocation(node, node.kernel, node.kernel_args, out, None)
            out.contents += c.stmts[0].contents
            
            cond = self._wl_loop_cond(self.pipe_ctx, node)
            self.cur_block.stmts.append(cgen.While(cgen.Line(cond), out))
            self.cur_block.stmts += self._wl_loop_post(node, cr)
           
        outlined = hasattr(node, '_nn')
        inoutline = outlined and (hasattr(self.kernel.anno, "outline") and not self.kernel.anno.outline.wrapper and self.kernel.anno.outline.pipe_name == node._nn)

        if outlined and inoutline:
            cr = self._inherit_pipe_ctx("pipe")
            wl_body()
            self._release_pipe_ctx(cr)
        else:
            cr = self._create_or_get_pipe_ctx(node.worklist_init, node, "wl")

            if not outlined:
                wl_body()
            else:
                out = []
                self._compile_pipe_invocation(node, node._nn, out)
                self.cur_block.stmts.append(out[0])

            if cr:
                self.cur_block.add_stmt("%s.free()" % (self.pipe_ctx,))

            self._release_pipe_ctx(cr)

    def visit_Block(self, node):
        self.blocks.push(GenericBlock())
        for s in node.stmts:
            self.visit(s)
        c = self.blocks.pop()

        self.cur_block.stmts.append(Block(c.decls + c.stmts))

    def visit_Pipe(self, node):
        def visit_PipeBody(n):
            self.visit(node.stmts)
                #TODO: pipe management?
        
        #TODO
        #assert self.kernel_block is None, "Can't use Pipe inside a kernel block"
        def pipe_body():
            visit_PipeBody(node)

            c = self.blocks.pop()
            out = c.stmts[0]

            if node.once:
                self.cur_block.stmts += self._wl_loop_entry(node)
                self.cur_block.stmts.append(out)
            else:
                cond = self._wl_loop_cond(self.pipe_ctx, node)
                self.cur_block.stmts.append(cgen.While(cond, out))

            self.cur_block.stmts += self._wl_loop_post(node, cr)
        
        outlined = hasattr(node, '_nn')
        #inoutline = outlined and (self.kernel.name == node._nn or self.kernel.name == node._nn + "_gpu" or self.kernel.name == node._nn + "_gpu_dev")
        inoutline = outlined and (hasattr(self.kernel.anno, "outline") and not self.kernel.anno.outline.wrapper and self.kernel.anno.outline.pipe_name == node._nn)
        if outlined and inoutline:
            cr = self._inherit_pipe_ctx("pipe")
            self.blocks.push(GenericBlock())
            pipe_body()
            self._release_pipe_ctx(cr)
        else:
            cr = self._create_or_get_pipe_ctx(node.init, node, "pipe")

            if not outlined:
                self.blocks.push(GenericBlock())
           
                if cr:
                    self.blocks.push(GenericBlock())

                pipe_body()

                if cr:
                    c = self.blocks.pop()
                    self.cur_block.stmts.append(Block(c.decls + c.stmts))

            else:
                out = []
                self._compile_pipe_invocation(node, node._nn, out)
                self.cur_block.stmts.append(out[0])

            if cr:
                self.cur_block.add_stmt("%s.free()" % (self.pipe_ctx,))

            self._release_pipe_ctx(cr)
                

    def visit_Iterate(self, node):
        assert node.kernel in self.kernels, "Kernel '%s' not found" % (node.kernel,)

        if node.condition == "ANY":
            self._compile_any(node)
        elif node.condition == "WL":
            self._compile_wl(node)

    def _decl_tb_sizes(self, unit):
        decl = set()
        for k in unit.kernels.values():
            if not (k.device or k.host):
                if k.has_anno("call_config"):
                    block = k.anno.call_config.block
                    if isinstance(block, (ShrinkableBlockTy, FixedBlockTy)):
                        if block.var in decl:
                            #TODO: make sure values are also the same?
                            continue

                        if block.size is None:
                            # TODO
                            self.cur_block.add_stmt("static const int %s = TB_SIZE" % (block.var))
                        else:
                            self.cur_block.add_stmt("static const int %s = %s" % (block.var, block.size))

                        decl.add(block.var)
                    elif isinstance(block, ElasticBlockTy):
                        # in principle this can be set at runtime, so skip it for now
                        pass
                        

    def visit_Module(self, node):
        self.blocks.push(ModuleBlock())
        
        out = self.cur_block

        out.decls += [cgen.Comment(" -*- mode: c++ -*- ")]
                      
        if "wlatomics" in self.compiler.options.instrument:
            out.decls.append(cgen.Define('COUNT_ATOMICS', ''))

        out.decls += [Include('gg.h', False),
                      Include('ggcuda.h', False), BlankLine(),
                      cgen.Statement("void kernel_sizing(%s &, dim3 &, dim3 &)" % (self.GRAPH_TYPE,)),
                      cgen.Define('TB_SIZE', 256), # hack
                      cgen.Statement('const char *GGC_OPTIONS = "%s"' % (self.compiler.options))]
        
        self._create_instr_vars()

        first_kernel = True

        for s in node.stmts.stmts:
            assert isinstance(s, TOP_LEVEL)
            if isinstance(s, gg.ast.Kernel) and first_kernel:
                self._decl_tb_sizes(self.unit)
                first_kernel = False
            self.visit(s)
        
        self.outputfile.write(str(out.to_block()))

def generate(outputfile, astinfo):
    w = CUDAPreGen(astinfo)
    w.visit(astinfo.ast)

    w = CUDAGen(astinfo)
    w.outputfile = outputfile
    w.visit(astinfo.ast)

if __name__ == "__main__":
    import sys
    ast = gg.ast.Module([gg.ast.Kernel("kernel", [('Graph', 'graph')],
                                     [gg.ast.CBlock(["printf('hellow world')"])]
                                     )
                        ])

    generate(sys.stdout, ast)
