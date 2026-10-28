import gg.types
from gg.ast import MethodInvocation
import gg.lib.anno 

class PushMethodInvocation(MethodInvocation):
    def clone(self):
        x = super(PushMethodInvocation, self).clone()
        x._coop_only = self._coop_only
        x._coop_method = self._coop_method
        
        if hasattr(self.anno, 'parcomb'):
            x.anno.parcomb = self.anno.parcomb.clone()

        return x

class WorklistIterator(gg.types.Iterator):
    def __init__(self, wl, offset=None, limit=None):
        super(WorklistIterator, self).__init__(offset, limit)
        self.wl = wl
    
    def iter_type(self):
        return "index_type"
    
    def start(self):
        return self.offset

    def end(self):
        if self.limit:
            return self.limit
        else:
            return "*((volatile %s *) (%s).dindex)" % (self.iter_type(), self.wl)

    def size(self):
        if self.offset != "0" or self.limit:
            return "(%s) - (%s) + 1" % (self.end(), self.start())
        else:
            return "*((%s).dindex)" % (self.wl)
         
         
class Worklist(gg.types.DataStructure):
    # TODO: serial methods, coop methods
    # TODO: names for in_wl and out_wl

    def __init__(self, wl = None):
        self.wl = wl # for named worklists, not yet supported
        
    def items(self, offset=None, limit=None):
        return WorklistIterator("in_wl", offset, limit)

    def pop(self, guard, ndx, into):
        return MethodInvocation("in_wl", "pop", "Worklist", [guard, ndx, into])

    def push(self, arg, _coop_only = False):
        n = "out_wl"
        if self.wl == "retry":
            n = "re_wl"

        m = PushMethodInvocation(n, "push", "Worklist", [arg])

        m._coop_only = _coop_only
        m._coop_method = MethodInvocation(n, "push_coop", "Worklist", [])

        if not _coop_only:
            m.anno.parcomb = gg.lib.anno.ParCombAnno(MethodInvocation(n, "push_id", "Worklist", []))
            m.anno.parcomb.combiner_method = MethodInvocation(n, "push_range", "Worklist", ['+count+'])
            m.anno.parcomb.combiner_type = "index_type"

            tm = MethodInvocation(n, "do_push", "Worklist", ['+start+', '+ndx+'])
            
            sm = {}
            sm['warp'] = MethodInvocation(n, "setup_push_warp_one", "Worklist", [])
            sm['thread'] = MethodInvocation(n, "push_range", "Worklist", ['+count+'])
            sm['threadblock'] = MethodInvocation(n, "push_tb", "Worklist", ['+count+'])

            m.anno.coopconv = gg.lib.anno.CoopConvAnno(tm, sm, "index_type")

        return m

#TODO: we should have a pop_prio to inform the compiler that the kernel
# wants workitems in priority order. This is more informative and
# useful than push_prio.

    def push_prio(self, arg, prio):
        return MethodInvocation("out_wl", "push_prio", "Worklist", [arg, prio])

    def print_size(self, it):
        return MethodInvocation("*pipe*", "print_size", "Worklist", [it])

    def display_items(self, it):
        return MethodInvocation("*pipe*", "display_items", "Worklist", [it])
