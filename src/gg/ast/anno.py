import collections
import gg.compiler

ClosureVariable = collections.namedtuple('ClosureVariable', ['name', 'decl', 'init', 'user'])
ArrayVarInfo = collections.namedtuple('ArrayVarInfo', ['name', 'maxsize'])


class ASTNodeAnno(object):
    "Namespace for compiler annotations on AST nodes. Each attribute on this class is dynamically attached and must be a class that descends from this"

    clonable = False
    
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            assert hasattr(self, k), "Attribute %s not found on %s" % (k, self.__class__.__name__)
            setattr(self, k, v)
         
    def clone_top(self):
        x = ASTNodeAnno()
        self._clone_helper(x)
        return x
    
    def clone(self):
        if self.clonable:
            raise NotImplementedError
        else:
            return None

    def _clone_helper(self, target, props = None):
        if not self.clonable: return None # delete me, except for top-level .anno
        if not props:
            props = list(vars(self).keys())

        for k, v in vars(self).items():
            if isinstance(v, ASTNodeAnno):
                ov = v.clone()
                if ov is not None:
                    setattr(target, k, ov)
            else:
                #TODO: shallow copy of attribute value!
                setattr(target, k, v)

        return target

class UniformAnno(ASTNodeAnno):
    clonable = True

    uniform = None    # this node is/must_be uniform if true (on branches and loops), is not uniform if False, don't know if None
    place_uniform = False  # this node must be placed at a focal point
    place_level = None   # level, similar to barriers (0 -- global, 1 -- local)

    def clone(self):
        return self._clone_helper(UniformAnno())

class NamedParentAnno(ASTNodeAnno):
    clonable = False
    number = None

    def __init__(self, number):
        self.number = number

def NamedParent(node, *args, **kwargs):
    node.anno.named_parent = NamedParentAnno(*args, **kwargs)
    return node
    
class ScopedOptimizationsAnno(ASTNodeAnno):
    clonable = True
    
    def clone(self):
        # TODO: should we always clone this? 
        # for oitergb, yes.
        x = self._clone_helper(ScopedOptimizationsAnno())
        x.from_dict(self._d)
        return x
    
    def to_dict(self):
        return {}

    def from_dict(self, d):
        self._d = d
        self.options = gg.compiler.CompilerOptions()
        self.options.from_dict(d)
        self.specified = set(d.keys())

def ScopedOptimizations(node, *args, **kwargs):
    node.anno.scoped_optimizations = ScopedOptimizationsAnno(*args, **kwargs)
    return node

class UniformCondAnno(ASTNodeAnno):
    clonable = True
    uniform_only = None
    _only_if_np = False # HACK

    def __init__(self, uniform_only, _only_if_np = False):
        self.uniform_only = uniform_only
        self._only_if_np = _only_if_np
    
    def clone(self):
        return self._clone_helper(UniformCondAnno(self.uniform_only, self._only_if_np))

class UnrollAnno(ASTNodeAnno):
    clonable = True
    unroll = False
    count = 0
    unrolled = False  # this is an unrolled statement

    def __init__(self, count = 0, unroll = True):
        self.unroll = unroll
        self.count = count

    def clone(self):
        return self._clone_helper(UnrollAnno())

class LaunchConfigAnno(ASTNodeAnno):
    blocks = "blocks"
    threads = "threads"

    def __init__(self, blocks = None, threads = None):
        if blocks: self.blocks = blocks
        if threads: self.threads = threads

class ClosureHintAnno(ASTNodeAnno):
    clonable = True

    def __init__(self, closure = None):
        self.user_closure = closure

    def clone(self):
        return self._clone_helper(ClosureHintAnno(self.user_closure))

class DisableAnno(ASTNodeAnno):
    clonable = True

    def __init__(self, *args):
        self.what = set(args)

    def clone(self):
        return self._clone_helper(DisableAnno(*list(self.what)))

class ClosureAnno(ASTNodeAnno):
    clonable = True
    decls = None
    init = None

    gpu_decls = None
    gpu_init = None

    _user = False

    # information in user_* will override/supplement information
    # automatically detected.

    user_decls = None
    user_init = None

    user_gpu_decls = None
    user_gpu_init = None

    var_list = None

    def __init__(self, saddr, xaddr, _user = True):
        """Provide declarations and initialization for the closure, as
        a list of tuples (variable, (type, declaration)) [note nesting] and 
        (variable, initialization)"""
        
        # ideally, we should have a type system setup that
        # automatically figures out gpu_decls and gpu_init from decls
        # and init as sketched in iteroutliner

        self.saddr = saddr
        self.xaddr = xaddr

        decls, init = saddr.to_closure_format()
        gpu_decls, gpu_init = xaddr.to_closure_format()

        vd = [x[0] for x in decls]
        dd = [x[0] for x in init]

        gvd = [x[0] for x in gpu_decls]
        gdd = [x[0] for x in gpu_init]

        assert vd == dd, "[cpu] Variables declared (%s) do not match those initialized (%s)" % (vd, dd)
        assert gvd == gdd, "[gpu] Variables declared (%s) do not match those initialized (%s)" % (gvd, gdd)

        assert gvd == vd, "CPU Variables declared (%s) do not match those declared on the GPU (%s)" % (vd, gvd)

        # TODO: check syntax of dd and gdd

        self.var_list = vd

        if _user:
            self.user_decls = dict(decls)
            self.user_init = dict(init)

            self.user_gpu_decls = dict(gpu_decls)
            self.user_gpu_init = dict(gpu_init)

            self.decls = dict()
            self.init = dict()

            self.gpu_decls = dict()
            self.gpu_init = dict()
        else:
            self.user_decls = dict()
            self.user_init = dict()

            self.user_gpu_decls = dict()
            self.user_gpu_init = dict()

            self.decls = dict(decls)
            self.init = dict(init)

            self.gpu_decls = dict(gpu_decls)
            self.gpu_init = dict(gpu_init)

    def has_var(self, var):
        return var in self.var_list # O(N)!

    def add(self, var, decl, init, gpu_decl, gpu_init):
        assert var not in self.var_list, "Variable %s already present in closure" % (var,)
        
        self.var_list.append(var)
        self.decls[var] = decl
        self.init[var] = init

        self.gpu_decls[var] = gpu_decl
        self.gpu_init[var] = gpu_init

    def items(self, src_dev, dst_dev):
        # TODO: all variables in varlist must be in decls/user_decls and vice versa.

        if src_dev == "cpu" and dst_dev == "cpu":
            decls = self.decls
            init = self.init
            user_decls = self.user_decls
            user_init = self.user_init
        elif (src_dev == "cpu" and dst_dev == "gpu") or (src_dev == "gpu" and dst_dev == "gpu"):
            decls = self.gpu_decls
            init = self.gpu_init
            user_decls = self.user_gpu_decls
            user_init = self.user_gpu_init
        elif src_dev == "gpu" and dst_dev == "cpu":
            assert False, "Not supported."

        for v in self.var_list:
            if v in user_decls:
                yield ClosureVariable(v, user_decls[v], user_init[v], True)
            else:                
                yield ClosureVariable(v, decls[v], init[v], False)
        
    def clone(self):
        if not self._user:
            return None
        else:
            return ClosureAnno(self.user_decls, self.user_init, self.user_gpu_decls, self.user_gpu_init)

class CallConfigAnno(ASTNodeAnno):
    clonable = True
    grid = None
    block = None

    def __init__(self, block, grid = None):
        self.block = block
        self.grid = grid

    def clone(self):
        return CallConfigAnno(self.block, self.grid)




class ArrayInfoAnno(ASTNodeAnno):
    """Pass sizes of GPU arrays for instrumentation"""
    clonable = True
    ainfo = None
    
    def clone(self):
        return ArrayInfoAnno(ainfo = self.ainfo)
    

def CallConfig(node, *args, **kwargs):
    node.anno.call_config = CallConfigAnno(*args, **kwargs)
    return node
            
# deprecated, do not use
def Annotation(astnode, **kwargs):
    for ann, value in kwargs.items():
        if ann == "uniform":
            assert False
            astnode.uniform = value
        else:
            assert False, "%s = %s unrecognized annotation" % (ann, value)
        
    return astnode

def Uniform(astnode, uniform = True, **kwargs):
    astnode.anno.uniform = UniformAnno(uniform = uniform, **kwargs)
    return astnode

def BlockDistribution(astnode, **kwargs):
    astnode.distribution = 'block'
    return Annotation(astnode, **kwargs)

def Unroll(astnode, **kwargs):
    astnode.anno.unroll = UnrollAnno(**kwargs)

    return astnode

def Closure(astnode, *args, **kwargs):
    if "_ignore" in kwargs and kwargs['_ignore']:
        return astnode

    astnode.anno.closure = ClosureAnno(*args, **kwargs)
    return astnode

def ClosureHint(astnode, *args, **kwargs):
    if "_ignore" in kwargs:
        if kwargs['_ignore']:
            return astnode

        del kwargs['_ignore']

    astnode.anno.closure_hint = ClosureHintAnno(*args, **kwargs)
    return astnode

def UniformConditional(astnode, uniform_only = True, _only_if_np = False):
    astnode.anno.uniform_cond = UniformCondAnno(uniform_only, _only_if_np)
    return astnode

def LaunchConfig(astnode, *args, **kwargs):
    astnode.anno.cuda_launch_config = LaunchConfigAnno(*args, **kwargs)
    return astnode

def Disable(astnode, *args, **kwargs):
    astnode.anno.disable = DisableAnno(*args, **kwargs)
    return astnode

def ArrayInfo(astnode, **kwargs):
    astnode.anno.array_info = ArrayInfoAnno(**kwargs)
    return astnode
