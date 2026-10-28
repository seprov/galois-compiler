import gg.ast.modifier
from gg.ast import Kernel, CBlock, Block, If, While, CDecl, CFor, LocalBarrier, ForAll, CondC, Assign, MethodInvocation, NOP
from gg.ast.anno import Uniform
from gg.ast.params import PipeParam
import gg.passes
from gg.ast.utils import *
import gg.passes.kanno
from gg.ast.misc import cblocks
from gg.ast.tools import EraseGen, Dumper
from . import np_sched
from gg.ast.callconfig import convert_to_fixed

TYPEDEFS = """
typedef cub::BlockScan<multiple_sum<2, {index_type}>, BLKSIZE> BlockScan
typedef union np_shared<BlockScan::TempStorage, {index_type}, {tb}, {wp}, {fg} > npsTy
"""

TYPEDEFS_SIMPLE = """
typedef cub::BlockScan<{index_type}, BLKSIZE> BlockScan
typedef union np_shared<BlockScan::TempStorage, {index_type}, {tb}, {wp}, {fg} > npsTy
"""

DECL_BEFORE = [('const int', 'BLKSIZE', '= __kernel_tb_size'),
               ('const int', 'ITSIZE', '= BLKSIZE * {np_factor}'),]
        
DECL_AFTER = [('__shared__ npsTy', 'nps', '')]

TB_Barrier = LocalBarrier

def CBlockNP(*args, **kwargs):
    return CBlock(*args, parse = False, **kwargs)

def cv_init(cvars):
    out = []

    for cv in cvars:        
        out.append("_np_closure[threadIdx.x].%s = %s" % (cv, cv))

    return CBlock(out)        

def init_cvars(cvars, source):
    out = []
    out.append("assert(%s < __kernel_tb_size)" % (source,))
    for cv in cvars:
        out.append("%s = _np_closure[%s].%s" % (cv, source, cv))

    return CBlock(out)

def get_schedulers(loop, chosen_schedulers, np_factor):
    schedulers = []
     # these are added in ascending order of their default range_min
    if 'fg' in chosen_schedulers:
        if np_factor == 1:
            schedulers.append(np_sched.NPFineGrained1)
        else:
            schedulers.append(np_sched.NPFineGrainedMulti)

    if 'wp' in chosen_schedulers:
        schedulers.append(np_sched.NPWarp)

    if 'tb' in chosen_schedulers:
        schedulers.append(np_sched.NPTB)
    
    mn = "0"
    for i, s in enumerate(schedulers[:-1]):
        schedulers[i] = schedulers[i](mn, schedulers[i+1].default_min, loop, len(schedulers))
        mn = schedulers[i+1].default_min

    schedulers[-1] = schedulers[-1](mn, "", loop, len(schedulers))

    schedulers.reverse()

    return schedulers

# offset buckets
def get_num_buckets(schedulers):
    num_buckets = 1
    last_non_multi_ndx = None

    for i, s in enumerate(schedulers):
        if s.multi_outer:
            if i > 0:
                num_buckets = 2
                last_non_multi_ndx = i - 1
            else:
                assert len(schedulers) == 1, "Multiple multi_outer schedulers are not currently supported"
            
            break

    if last_non_multi_ndx is not None:
        # the assumption that schedulers are all non-multi followed by
        # multi is strictly not necessary, but saves us from having to
        # save and restore np_start and also simplifies(?) compiler code.

        assert all([not x.multi_outer for x in schedulers[:last_non_multi_ndx]])
        assert all([x.multi_outer for x in schedulers[last_non_multi_ndx+1:]])
    else:
        last_non_multi_ndx = len(schedulers) - 1

    return (num_buckets, last_non_multi_ndx)

def assign_buckets(num_buckets, schedulers):
    if num_buckets == 1:
        return
        
    multi_bucket_assigned = False

    for s in schedulers:
        if s.multi_outer:
            assert not multi_bucket_assigned, "Multiple multi_outer schedulers are not currently supported"
            s.offset_bucket = 1
            multi_bucket_assigned = True
        else:
            s.offset_bucket = 0
            
def prefix_sum(loop, schedulers):
    num_buckets, last_non_multi_ndx = get_num_buckets(schedulers)
    assign_buckets(num_buckets, schedulers)

    out = []

    comb_start_shared = [('__shared__ ' + s.ty, '_np_pc_' + s.name, '') for s, n in loop.comb_starts.values()]

    out.append(CondC(num_buckets == 1, 
                     CDecl([("%s" % (loop.index_type,), 
                             "_np_mps", ""),
                            ("%s" % (loop.index_type,), 
                             "_np_mps_total", ""),
                            ]),
                     CDecl([("multiple_sum<2, %s>" % (loop.index_type,), # TODO: 2 -> num_buckets?
                             "_np_mps", ""),
                            ("multiple_sum<2, %s>" % (loop.index_type,), 
                             "_np_mps_total", ""),
                            ]),                    
                     )
               )

    assert schedulers[-1].range_min == "0", "Last scheduler must have range_min of `0'"

    # obsolete: separated to keep _np.total accurate for [1]
    out += [CondC(num_buckets == 1,
                  CBlock(["_np_mps = _np.size"]),
                  CBlock(["_np_mps.el[0] = _np.size >= %s ? _np.size : 0" % (schedulers[last_non_multi_ndx].range_min),
                          # note: if there are multiple multi_outer, then this must be for each scheduler
                          "_np_mps.el[1] = _np.size < %s ? _np.size : 0"  % (schedulers[last_non_multi_ndx].range_min),
                          ]),                  
                  ),
            CBlock("BlockScan(nps.temp_storage).ExclusiveSum(_np_mps, _np_mps, _np_mps_total)"),
            CondC(loop.comb_present, CDecl(comb_start_shared))
            ]

    return out
    

def get_comb_start_inits(loop, schedulers):
    def change_rhs(assign_node_rhs):
        assert isinstance(assign_node_rhs, MethodInvocation), assign_node_rhs
        assert len(assign_node_rhs.args) == 1, len(assign_node_rhs.args)
        
        num_buckets = set([x.offset_bucket for x in schedulers])

        if len(num_buckets) == 1:
            assign_node_rhs.args[0] = "_np_mps_total"
        else:
            assign_node_rhs.args[0] = " + ".join(["_np_mps_total.el[%d]" % (i,) for i in range(0, len(num_buckets))])

        return assign_node_rhs

    return [Assign("_np_pc_" + s.name, change_rhs(n.rhs)) for s, n in loop.comb_starts.values()]

def NP1_Template(chosen_schedulers, size, start, index_var, index_type, np_factor, work, comb_sym, comb_starts, cl):
    loop = np_sched.NPLoop()
    loop.work = work
    loop.index_type = index_type
    loop.index_var = index_var
    loop.comb_present = len(comb_sym) > 0
    loop.comb_starts = comb_starts
    loop.comb_sym = comb_sym
    
    loop.closure_present = cl is not None
    loop.closure_variables = [] if not loop.closure_present else cl.var_list        

    out = []
    out.append(CDecl(("struct NPInspector1","_np", "= {0,0,0,0,0,0}")))

    if loop.closure_present:
        closure_struct = "; ".join(["%s %s" % (n.decl[0], n.decl[1]) for n in cl.items("cpu", "cpu")]) + ";" # cpu,cpu is correct
        out.append(CDecl(("__shared__ struct { %s }" % (closure_struct,), "_np_closure", "[TB_SIZE]")))
        out.append(cv_init(loop.closure_variables)) # outside pop since we restore from it, else main loop gets messed up

    # initialize nested loop indices
    out.append(If("pop", [CBlock(["_np.size = " + size, 
                                  "_np.start = " + start])]))

    schedulers = get_schedulers(loop, chosen_schedulers, np_factor)
    #for s in schedulers:
    #    print s.__class__.__name__, s.range_min, s.range_max

    out += prefix_sum(loop, schedulers)

    sinit = []
    for s in schedulers:
        sinit += s.shared_init()

    out.append(If("threadIdx.x == 0", 
                  sinit + 
                  get_comb_start_inits(loop, schedulers)
                  )
               )

    out.append(TB_Barrier().sync())

    for s in schedulers:
        out += s.pre()
        out += s.sched()
        out += s.post()

    out.append(CondC(loop.closure_present, init_cvars(loop.closure_variables, "threadIdx.x")))

    return schedulers, out

class ForAllNPAnno(gg.ast.ASTNodeAnno):
    perform_np = False
    np_failed = False
    np_failed_reason = None
    reads_external = None
    writes_external = None
    ext_reads = None
    ext_writes = None
    clonable = False
    done = False

    def __init__(self, *args, **kwargs):
        self.ext_reads = set()
        self.ext_writes = set()
        super(ForAllNPAnno, self).__init__(*args, **kwargs)

    def clone(self):
        return self._clone_helper(ForAllNPAnno())

class ForAllChecksForNP(gg.ast.walkers.ASTPreOrderWalker):
    def generic_node_visitor(self, node):
        if isinstance(node, ForAll):
            if not node.check_gen(self.gen):
                # check_gen can be optional to allow re-checking nodes whose contents have changed? 
                # Or require changers to clone always? [current code assumes this]
                return True

            if not self.unit.get_opt_value("np", node, self.compiler):
                assert not node.has_anno("forall_np")
                node.anno.forall_np = ForAllNPAnno(perform_np = False)
                return True

            if node.nesting_level != 2:
                assert not node.has_anno("forall_np")
                node.anno.forall_np = ForAllNPAnno(perform_np = False)
                return True

            if not node.symtab.lookup("pop"):
                self.compiler.log.warning("No guarding pop found, not applying Nested Parallelism")
                node.anno.forall_np = ForAllNPAnno(perform_np = False)
                return True

            x = cblocks.ClosureEnvironment()
            complete, symbols, reads, writes = x.get_environment_rw(self.compiler, node)

            if not complete:
                node.anno.forall_np = ForAllNPAnno(perform_np = False, np_failed = True, np_failed_reason = "Incomplete closure computation")
                self.compiler.log.warning("Closure environment computation was incomplete, not applying Nested Parallelism")
                return True

            os = set()
            loc = set()
            comb_starts = set()
            for n, s in symbols.items():
                if not (s.param or s.gl):                        
                    os.add(n)
                    ss = node.symtab.lookup(n)
                    if ss is not None:
                        if ss.comb_start:
                            ss._node = node
                            os.remove(n)

                    if (node.symtab.lookup(n, recurse = False) is not None)  or node.stmts.symtab.lookup(n, recurse = False) is not None:
                        loc.add(n)

            if os != loc:
                diff = os.difference(loc)
                out = []
                wr = False
                for s in diff:
                    o = s
                    if s in reads:
                        o += " [R]"

                    if s in writes:
                        o += " [W]"
                        wr = True
                    out.append(o)

                if not wr:
                    if not node.has_anno('closure'):
                        self.compiler.log.warning("Nested ForAll refers to non-local/non-iterator variables ('%s') but closure is absent, not applying", "', '".join(diff))
                        node.anno.forall_np = ForAllNPAnno(perform_np = False, np_failed = True, np_failed_reason = "Non-local/non-iterator variable reads ('%s') with no closure" % ("', '".join(diff)))
                        return True
                else:
                    if "allow_np_writes" in self.compiler.options.hacks:
                        self.compiler.log.info("Skipping (hack: allow_np_writes) Nested ForAll writes to non-local/non-iterator variables ('%s')", "', '".join(out))
                    else:
                        self.compiler.log.warning("Nested ForAll writes to non-local/non-iterator variables ('%s'), not applying Nested Optimization", "', '".join(out))
                        node.anno.forall_np = ForAllNPAnno(perform_np = False, np_failed = True, np_failed_reason = "Non-local/non-iterator variable writes ('%s')" % ("', '".join(out)))
                        return True

            if node.has_anno("closure"):
                cl = node.anno.closure
                if len(os) > 0:
                    nvl = []
                    for v in cl.var_list:
                        s = node.symtab.lookup(v)
                        if not (s.param or s.gl): # This should actually be definition(s) == param/global.
                            nvl.append(v)

                    cl.var_list = nvl
                else:
                    # ClosureHint with an `empty' closure (i.e. only params and globals)
                    cl.var_list = []

            node.anno.forall_np = ForAllNPAnno(perform_np = True, reads_external = len(reads) > 0, ext_reads = reads, writes_external = len(writes) > 0, ext_writes = writes)

            return True
        else:
            return True

class NP1(gg.ast.modifier.ASTModifierST):
    def __init__(self):
        super(NP1, self).__init__()
        
    def visit_Kernel(self, node):
        self.kernel = node
        self.decl_nest = None
        self.in_np = False
        self.comb_starts = {}  # technically, this is on the scope of a block ... currently prevents multiple comb_starts

        super(NP1, self).visit_Kernel(node)
        if self.decl_nest:
            self.nodes_generated = True

            # Change to FixedBlock regardless of whether TB scheduler is used since
            # data structures for warp/thread also use fixed TB size
            convert_to_fixed(node, self.unit)

            # if hasattr(node, '_blkscan') and node._blkscan == True:
            #     dn = self.decl_nest.stmts[3:]
            # else:
            #     dn = self.decl_nest
            #     node._blkscan = True

            crossover_decls = CDecl([("const int", '_NP_CROSSOVER_WP', '= 32'),
                                     ("const int", '_NP_CROSSOVER_TB', '= __kernel_tb_size')])

            # TODO: fix this
            #if self.schedulers_len == 1:
            #    node.stmts.stmts.insert(0, NOP())
            #else:
            node.stmts.stmts.insert(0, crossover_decls)

            node.stmts.stmts.insert(1, self.decl_nest[0])
            node.stmts.stmts.insert(2, self.decl_nest[1])
            node.stmts.stmts.insert(3, self.decl_nest[2])

        self.kernel = None
        return node

    def node_comb_symbols(self, forall_node):
        assert isinstance(forall_node, ForAll)

        # TODO: this is a hack, ideally we want to check all
        # references to offset variables, not just peek at the symbol
        # table

        out = set()
        for s in forall_node.symtab.symbols.values():
            if s.comb_offset:
                out.add(s)

        return out

    def _get_scheduler_structs(self, schedulers):
        S = {'tb': 'struct tb_np',
             'wp': 'struct warp_np<__kernel_tb_size/32>',
             'fg': 'struct fg_np<ITSIZE>'}

        out = {}
        for x, y in S.items():
            if x in schedulers:
                out[x] = y
            else:
                out[x] = 'struct empty_np'

        return out

    def visit_ForAll(self, node):
        # TODO: The ForAll node should be uniform

        if node.check_gen(self.gen) and node.has_anno("forall_np") and node.anno.forall_np.perform_np:
            self.in_np = True
            super(NP1, self).visit_ForAll(node)
            self.in_np = False
            
            self.compiler.log.info("Applying Nested Parallelism to %s" % (node,))            
            
            comb_symbols = self.node_comb_symbols(node)

            nvi = node.ndxvar.iterator
            nv = node.ndxvar
            assert self.decl_nest is None

            decls1 = CDecl([(x, y, z.format(np_factor = self.compiler.options.np_factor)) for (x, y, z) in DECL_BEFORE])

            decls2 = CDecl([(x, y, z.format(np_factor = self.compiler.options.np_factor)) for (x, y, z) in DECL_AFTER], dont_move = True)

            schedulers = self.unit.get_opt_value("np_schedulers", node, self.compiler)

            np_sched_structs = self._get_scheduler_structs(schedulers)

            if node.has_anno("closure"):
                cl = node.anno.closure
            else:
                cl = None

            schedulers2, rv = NP1_Template(schedulers, nvi.size(), nvi.start(), nv.var_name, nv.var_type, self.compiler.options.np_factor, node.stmts, comb_symbols, self.comb_starts, cl)
            num_buckets = len(set([x.offset_bucket for x in schedulers2]))

            node.anno.forall_np.done = True

            if num_buckets == 1:
                TY = TYPEDEFS_SIMPLE.format(index_type = nvi.iter_type(), **np_sched_structs)
            else:
                TY = TYPEDEFS.format(index_type = nvi.iter_type(), **np_sched_structs)

            self.decl_nest = [decls1, CBlockNP(TY.split("\n")), decls2]
            self.nodes_generated = True

            return rv
        
        super(NP1, self).visit_ForAll(node)
        
        if self.decl_nest and node.nesting_level == 1:
            return Uniform(node)
        
        return node

    def visit_Assign(self, node):
        if node.check_gen(self.gen) and node.has_anno("cc_setup"):
            s = self.symtab.top.lookup(node.lhs)
            if s.comb_start:
                if hasattr(s, '_node'):
                    fa = s._node
                    if fa.has_anno("forall_np"):
                        if fa.anno.forall_np.perform_np:
                            assert s.name not in self.comb_starts, "Duplicate comb_start symbol %s" % (s.name,)
                            self.compiler.log.debug('comb_start %s recognized' % (s.name,))
                            self.comb_starts[s.name] = (s, node)
                            self.nodes_generated = True

                            delattr(s, "_node") # ForAll will disappear after being np-ified
                            return []
                        else:
                            self.compiler.log.debug('comb_start %s ignored since loop will not be np-ified' % (s.name,))       
                    else:
                        self.compiler.log.debug('comb_start %s ignored, loop does not have forall_np annotation' % (s.name,))
                else:
                    self.compiler.log.debug("Node missing on comb_start symbol %s" % (s.name,))


        return node

    def visit_ReturnFromParallelFor(self, node):
        node._in_np = self.in_np
        return node

class NestedParallelismPass(gg.passes.Pass):
    depends = set(['KernelPropsPass', 'SemCheckedASTAvail', 'RWSetsPass', 'ClosureBuilderPass',
                   'PreOptimizationPass'])

    def run(self, compiler, unit, gen, pm):        
        v = ForAllChecksForNP()
        v.visit4(compiler, unit, unit.ast, gen)

        v = NP1()
        #v.schedulers = compiler.options.np_schedulers
        v.nodes_generated = False
        v.visit3(compiler, unit, unit.ast, gen)
        if v.nodes_generated: pm.set_nodes_generated()

        return True
