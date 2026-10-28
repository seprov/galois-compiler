import gg.ast.walkers
import gg.ast
import gg.passes
import gg.lib.wl

CC_ALL = 1
CC_ANY = 2
CC_WL = 3

class KernelEntryExitAnno(gg.ast.ASTNodeAnno):
    at_entry = None
    at_exit = None
    decls = None
    clonable = True

    def __init__(self, *args, **kwargs):
        super(KernelEntryExitAnno, self).__init__(*args, **kwargs)

        self.at_entry = []
        self.at_exit = []
        self.decls = {}

    def clone(self):
        return self._clone_helper(KernelEntryExitAnno())

class ScopedWalker(gg.ast.walkers.ASTWalker):
    def __init__(self):
        self.kernels = []
        self.kernel = None

    def visit_Kernel(self, node):
        self.kernels.append(self.kernel)
        self.kernel = node

        super(ScopedWalker, self).visit_Kernel(node)
        self.kernel = self.kernels.pop()

class KernelProps(ScopedWalker):
    nesting_level = 0
    pipe_nesting_level = 0
    loop_id = 0

    def visit_Kernel(self, node):
        if node.check_gen(self.gen):
            #TODO: need to overhaul this?
            node.contains_rfpf = False
            node.contains_wl = False
            node.writes_wl = False
            node.prio_wl = False
            node.contains_barrier = False
            node.barrier_level = -1
            node.contains_exclusive = False 
            node.call_contexts = set()
            node.contains_retry = False
            node.retry_merges = set()
            node.outer_forall_is_wl = False
            node.outer_forall_iterator = None
            node.anno.entry_exit = KernelEntryExitAnno()

            if node.name == "gg_main":
                node.host = True

        #TODO: Prune
        super(KernelProps, self).visit_Kernel(node)

    def visit_Retry(self, node):
        self.kernel.contains_retry = True
        self.kernel.contains_wl = True

        if hasattr(node, "merge"):
            self.kernel.retry_merges.add(node.merge)

    def visit_ReturnFromParallelFor(self, node):
        self.kernel.contains_rfpf = True

    def visit_MethodInvocation(self, node):
        # this is a hack until we resolve Worklist_Params
        if node.obj_type == "Worklist":
            if node.method not in ("print_size", "display_items"):
                self.kernel.contains_wl = True

            #TODO: need a base method form!
            if node.method in ("push", "push_prio", "push_id", "push_range", "do_push"):
                self.kernel.writes_wl = True
                if node.method == "push_prio":
                    self.kernel.prio_wl = True #TODO: need a prio read?
            elif node.method == "pop":
                pass
            elif node.method in ("setup_push_warp_one"):
                pass
            else:
                self.compiler.log.warning("Unknown method '%s' on Worklist" % (node.method,))
        elif isinstance(node.obj, gg.ast.HierarchicalBarrier):
            if node.method == "sync":
                self.kernel.contains_barrier = True
                self.kernel.barrier_level = min(node.obj.level, self.kernel.barrier_level) if self.kernel.barrier_level != -1 else node.obj.level
        
    def visit_Exclusive(self, node):
        #TODO: this might be backend dependent
        self.kernel.contains_barrier = True
        self.kernel.barrier_level = 0
        self.kernel.contains_exclusive = True

        super(KernelProps, self).visit_Exclusive(node)

    def _enter_loop(self, node):
        self.nesting_level += 1

        if node.check_gen(self.gen):
            self.loop_id += 1

            node.nesting_level = self.nesting_level
            node.loop_id = self.loop_id

    def _exit_loop(self, node):
        self.nesting_level -= 1

    def _enter_pipe(self, node):
        self.pipe_nesting_level += 1
        
        if node.check_gen(self.gen):
            node.nesting_level = self.pipe_nesting_level

    def _exit_pipe(self, node):
        self.pipe_nesting_level -= 1

    def visit_DoWhile(self, node):
        self._enter_loop(node)
        super(KernelProps, self).visit_DoWhile(node)
        self._exit_loop(node)

    def visit_Pipe(self, node):
        self._enter_pipe(node)

        super(KernelProps, self).visit_Pipe(node)
        self._exit_pipe(node)

    def visit_Iterate(self, node):
        self._enter_pipe(node)
        super(KernelProps, self).visit_Iterate(node)
        self._exit_pipe(node)

    def visit_While(self, node):
        self._enter_loop(node)
        super(KernelProps, self).visit_While(node)
        self._exit_loop(node)

    def visit_ForAll(self, node):
        self._enter_loop(node)

        if node.nesting_level == 1:
            if self.kernel.outer_forall_iterator is None:
                self.kernel.outer_forall_iterator = node.iterator

        if isinstance(node.iterator, gg.lib.wl.WorklistIterator):
            self.kernel.contains_wl = True

            if node.nesting_level == 1:
                self.kernel.outer_forall_is_wl = True

                if node.iterator.wl not in ('in_wl',):
                    self.kernel.outer_forall_arg_idx = [x[1] for x in self.kernel.args].index(node.iterator.wl)
                else:
                    self.kernel.outer_forall_arg_idx = -1

        super(KernelProps, self).visit_ForAll(node)

        self._exit_loop(node)

    def visit_For(self, node):
        self._enter_loop(node)

        if isinstance(node.iterator, gg.lib.wl.WorklistIterator):
            self.kernel.contains_wl = True

        super(KernelProps, self).visit_For(node)

        self._exit_loop(node)

    def visit_CFor(self, node):
        self._enter_loop(node)

        super(KernelProps, self).visit_CFor(node)

        self._exit_loop(node)


class KernelCallContexts(ScopedWalker):
    def __init__(self, astinfo):
        super(KernelCallContexts, self).__init__()
        self.astinfo = astinfo
        assert hasattr(self.astinfo, 'kernels')

    def visit_Invoke(self, node):
        pass

    def visit_Iterate(self, node):
        if node.condition == "ANY":
            self.astinfo.kernels[node.kernel].call_contexts.add(CC_ANY)
        elif node.condition == "ALL":
            self.astinfo.kernels[node.kernel].call_contexts.add(CC_ALL)
        elif node.condition == "WL":
            self.astinfo.kernels[node.kernel].call_contexts.add(CC_WL)
        else:
            assert False

        super(KernelCallContexts, self).visit_Iterate(node)

class KernelPropsPass(gg.passes.Pass):
    depends = set(['KernelListPass'])
    loop_id = 0

    def run(self, compiler, unit, gen, pm):
        w = KernelProps()

        w.loop_id = self.loop_id
        w.visit3(compiler, unit.ast, gen)
        self.loop_id = w.loop_id

        #TODO: add a pass that checks for duplicate loop_ids

        return True

class KernelCallContextsPass(gg.passes.Pass):
    depends = set(['SemCheckedASTAvail', 'KernelPropsPass'])
    
    def run(self, compiler, unit, gen, pm):
        w = KernelCallContexts(unit)
        w.visit3(compiler, unit.ast, gen)
        return True
        
