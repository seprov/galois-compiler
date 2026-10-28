import gg.types
from gg.ast import MethodInvocation, CDecl, CBlock
import gg.lib.wl

class AppendOnlyListIterator(gg.lib.wl.WorklistIterator):
    pass
         
class AppendOnlyList(gg.types.DataStructure):
    # TODO: serial methods, coop methods
    # TODO: names for in_wl and out_wl

    def __init__(self, l = None):
        self.list = l # for named worklists, not yet supported
    
    def declare(self, size = None):
        if size:
            return CDecl(("AppendOnlyList", self.list, "(%s)" % size))
        else:
            return CDecl(("AppendOnlyList", self.list, ""))

    def construct(self, size):
        return CBlock("%s = AppendOnlyList(%s)" % (self.list, size))

    def pop(self, dst, ndx, into):
        return MethodInvocation(self.list, "pop", "AppendOnlyList", [dst, ndx, into])

    def items(self, offset=None, limit=None):
        return AppendOnlyListIterator(self.list, offset, limit)

    def push(self, arg, _coop_only = False):
        m = MethodInvocation(self.list, "push", "AppendOnlyList", [arg])
        m._coop_only = _coop_only
        m._coop_method = MethodInvocation(self.list, "push_coop", "AppendOnlyList", [])

        if not m._coop_only:
            tm = MethodInvocation(self.list, "do_push", "AppendOnlyList", ['+start+', '+ndx+'])

            sm = {}
            sm['warp'] = MethodInvocation(self.list, "setup_push_warp_one", "AppendOnlyList", [])
            sm['thread'] = MethodInvocation(self.list, "setup_push_thread", "AppendOnlyList", ['+count+'])

            m.anno.coopconv = gg.lib.anno.CoopConvAnno(tm, sm, "index_type")

        return m

    #def push(self, arg):
    #    return MethodInvocation(self.list, "push", "AppendOnlyList", [arg])

#TODO: we should have a pop_prio to inform the compiler that the kernel
# wants workitems in priority order. This is more informative and
# useful than push_prio.

    def display(self):
        return MethodInvocation(self.list, "display", "AppendOnlyList", [])

    def param(self, ref = False):
        return gg.ast.params.AppendOnlyListParam(self.list, ref)

