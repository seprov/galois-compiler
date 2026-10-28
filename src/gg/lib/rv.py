import gg.types
from gg.ast import MethodInvocation
import gg.lib.anno 
from gg.passes.kanno import KernelEntryExitAnno

class ReturnInvocation(MethodInvocation):
    def __init__(self, *args, **kwargs):
        super(ReturnInvocation, self).__init__(*args, **kwargs)

        tm = MethodInvocation(self.obj, "do_return", "RV", self.args)
        sm = {}

        aee = KernelEntryExitAnno()
        aee.at_entry.append("ret_val.thread_entry()")
        aee.at_exit.append("ret_val.thread_exit<_br>(_ts)")
        aee.decls['br'] = ["typedef cub::BlockReduce<int, TB_SIZE> _br", "__shared__ _br::TempStorage _ts"]

        tm.anno.at_entry_exit = aee

        self.anno.coopconv = gg.lib.anno.CoopConvAnno(tm, sm, "int")

class RV(gg.types.DataStructure):
    def __init__(self, rv = None):
        self.rv = rv # for named worklists, not yet supported
        
    def return_(self, retval):
        return ReturnInvocation(self.rv, "return", "RV", [retval])

