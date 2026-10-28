# special parameter types known to the compiler and runtime

PARAM_WL = '+Worklist+'
PARAM_LOCK = '+Lock+'
PARAM_LOCKARRAY = '+LockArray+'
PARAM_GRAPH_REF = '+Graph&+'
PARAM_GRAPH = '+Graph+'
PARAM_APPEND_ONLY_LIST = '+AppendOnlyList+'
PARAM_APPEND_ONLY_LIST_REF = '+AppendOnlyList&+'
PARAM_PIPE_REF = '+Pipe&+'
PARAM_PIPE = '+Pipe+'
PARAM_EXCLUSIVE_LOCKS = "+ExclusiveLocks+"
PARAM_GLOBAL_BARRIER = "+GlobalBarrier+"
PARAM_RETVAL = "+RetVal+"

LOCKARRAY_SIMPLE = '+LockArray+'
LOCKARRAY_TICKET = '+LockArray<Ticket>+'
PARAM_LOCKARRAY_TICKET = LOCKARRAY_TICKET

def AppendOnlyListParam(list_name, ref = False):
    if ref:
        return (PARAM_APPEND_ONLY_LIST_REF, list_name)
    else:
        return (PARAM_APPEND_ONLY_LIST, list_name)

def GraphParam(graph_name, ref = False):
    if ref:
        return (PARAM_GRAPH_REF, graph_name)
    else:
        return (PARAM_GRAPH, graph_name)

def ExclusiveLocksParam(name):
    return (PARAM_EXCLUSIVE_LOCKS, name)

def GlobalBarrierParam(name):
    return (PARAM_GLOBAL_BARRIER, name)

def RetValParam(name):
    return (PARAM_RETVAL, name)

def WLParam(wlist_name):
    return (PARAM_WL, wlist_name)

def LockParam(lock_name):
    return (PARAM_LOCK, lock_name)

def LockArrayParam(lockarray_name, ty = LOCKARRAY_SIMPLE):
    return (ty, lockarray_name)

def PipeParam(pipe_name, ref = False):
    if ref:
        return (PARAM_PIPE_REF, pipe_name)
    else:
        return (PARAM_PIPE, pipe_name)

# TODO: ultimately move this to the AST
class Param(object):
    def __init__(self, param):
        assert isinstance(param, tuple)
        assert len(param) == 2
        assert isinstance(param[0], str) 
        assert isinstance(param[1], str) 

        self.param = param
        self.ty = param[0]
        self.name = param[1]

    def is_ref(self):
        return "&" in self.ty
    
    def make_ref(self):
        if self.ty[0] == "+":
            return "+"+self.ty[1:-1]+"&+"
        
        return self.ty + "&" # obviously wrong...

    # this can give wrong answers. 
    def is_primitive(self):
        if self.ty[0] == "+":
            return False
        
        # give up on templates, may return False for template::typedef
        if "<" in self.ty or "::" in self.ty:
            return False

        #TODO: this is not correct, esp. with templates, 
        # may want to parse this...
        for ty in ('char', 'int', 'float', 'double', 'signed', 'unsigned', 'short', 'long'):
            if ty in self.ty:
                return True
        
        # what about stdint types? size_t, ptrdiff_t, etc.

        return None # note the None

    
