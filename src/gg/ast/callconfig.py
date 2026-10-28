import toposort
import ast
from functools import reduce
#import re

#ID_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

class ExtractNames(ast.NodeVisitor):
    def visit_Name(self, node):
        self.names.append(node.id)

    @staticmethod    
    def get_names(node):
        x = ExtractNames()
        x.names = []
        try:
            nast = ast.parse(str(node))
        except:
            # need to log this!
            return []
            
        x.visit(nast)  # TODO: use already existing C name extraction?
        
        return x.names

def build_constants_table(symbols):
    """Takes a dict of symbols: expr where expr is an eval-able expr,
       returns a dict of symbol: literal-values"""

    deps = {}
    for s, v in symbols.items():
        n = ExtractNames.get_names(v)
        deps[s] = set(n)

    # if there is a cyclic dependency, this will raise ValueError
    order = toposort.toposort_flatten(deps)

    out = {}
    for s in order:
        v = symbols[s]
        if isinstance(v, str):
            try:
                val = eval(v, {}, out)
                out[s] = val
            except SyntaxError:
                # TODO: unable to evaluate v!
                out[s] = v
        else:
            out[s] = v

    return out

def convert_to_fixed(fn_node, unit):
    assert fn_node.has_anno("call_config")

    cc = fn_node.anno.call_config
    if not isinstance(cc.block, FixedBlockTy):                
        cc.block = FixedBlockTy(var = cc.block.var, size = cc.block.size)

    if fn_node.has_anno("original_kernel"):
        k = unit.kernels[fn_node.anno.original_kernel.name]
        convert_to_fixed(k, unit)

class CCBlockTy(object):
    pass

class FixedBlockTy(CCBlockTy):
    def __init__(self, var, size):
        self.var = var
        self.size = size # can be symbolic!

    def replaceable_by(self, y):
        if isinstance(y, (ElasticBlockTy, ShrinkableBlockTy)):
            return False

        if isinstance(y, FixedBlockTy):
            if self.var == y.var:
                return True

            if self.size == y.size:
                return True

        return False

    def __str__(self):
        return "FixedBlockTy(%s, %s)" % (self.var, self.size,)
    
    __repr__ = __str__

class ShrinkableBlockTy(CCBlockTy):
    def __init__(self, var, size):
        self.var = var        
        self.size = size # can be symbolic!
                          
    def replaceable_by(self, y):
        if isinstance(y, ElasticBlockTy):
            return False

        if isinstance(y, ShrinkableBlockTy):
            return (self.var == y.var) or (self.size == y.size)

        if isinstance(y, FixedBlockTy):
            return self.size > y.size # TODO: handling symbolic?

        assert False

    def __str__(self):
        return "ShrinkableBlockTy(%s, %s)" % (self.var, self.size,)
    
    __repr__ = __str__

class ElasticBlockTy(CCBlockTy):
    def __init__(self, var, size):
        self.var = var
        self.size = size # almost always symbolic!

    def replaceable_by(self, y): 
        if isinstance(y, (ElasticBlockTy, ShrinkableBlockTy, FixedBlockTy)):
            return True

        assert False
        
    def __str__(self):
        return "ElasticBlockTy(%s, %s)" % (self.var, self.size,)
    
    __repr__ = __str__


# def call_config_compat_p(kernel_cc, callee_cc, constants):
#     resolved_constants = build_constants_table(constants)
#     shrinkable = []
#     fixed = []
    
#     for c in callee_cc + [kernel_cc]:
#         if isinstance(c, ShrinkableBlockTy):
#             shrinkable.append((c.var, resolved_constants[c.size]))
#         elif isinstance(c, FixedBlockTy):
#             fixed.append((c.var, resolved_constants[c.size]))
#         else:
#             pass # for now
    
#     if len(shrinkable):
#         tbsize_shr = min([x[1] for x in shrinkable])
#     else:
#         tbsize_shr = -1
    
#     tbsize_fixed = set([x[1] for x in fixed])

#     if len(tbsize_fixed) > 1:
#         # call includes two fixed kernels which don't have the same fixed size!
#         return False, None
#     elif len(tbsize_fixed) == 1:
#         tbsize_fixed = tbsize_fixed.pop()

#         # constraint is that kernel_cc.var = all_eq(fixed)
#         if len(shrinkable):
#             # add constraint that kernel_cc.var <= min(shr)
#             return tbsize_shr >= tbsize_fixed, FixedBlockTy(kernel_cc.var, tbsize_fixed) 
#         else:
#             return True, FixedBlockTy(kernel_cc.var, tbsize_fixed)
#     else:
#         # constraint is that kernel_cc.var <= min(shr)
#         if len(shrinkable):
#             return True, ShrinkableBlockTy(kernel_cc.var, tbsize_shr)
#         else:
#             assert False, "Caller does not include callee kernels"


def call_config_compat_p(kernel_cc, callee_cc, constants):
    resolved_constants = build_constants_table(constants)
    allowed = []
    ILLEGAL_TB_SIZE = 1024+32

    for c in callee_cc + [kernel_cc]:
        if isinstance(c, ShrinkableBlockTy):
            allowed.append(set(range(32, resolved_constants[c.size]+1, 32)))
        elif isinstance(c, FixedBlockTy):
            allowed.append(set([resolved_constants[c.size]]))
        elif isinstance(c, ElasticBlockTy):
            allowed.append(set(range(32, ILLEGAL_TB_SIZE+1, 32)))
        else:
            assert False, c

    result = reduce(lambda x, y: x.intersection(y), allowed)
    
    if len(result) == 0:
        # call includes two fixed kernels which don't have the same fixed size, 
        # or a fixed kernel with a tbsize greater than all shrinkable tbsizes, etc.
        return False, None
    elif len(result) == 1:
        tbsize = result.pop()
        # constraint is that kernel_cc.var = all_eq(fixed)
        # also constraint that kernel_cc.var <= min(shr) if shr exists

        return True, FixedBlockTy(kernel_cc.var, tbsize) 
    else:
        # constraint is that kernel_cc.var <= min(shr) [which is max(tbsizes)]
        tbsize = max(result)
        if tbsize == ILLEGAL_TB_SIZE:
            return True, ElasticBlockTy(kernel_cc.var, None)
        else:
            return True, ShrinkableBlockTy(kernel_cc.var, tbsize)

def test_cccp_shr_one():
    "Test with one callee and identical bounds on caller"
    
    caller = ShrinkableBlockTy("caller", "TB_SIZE")
    callee = [ShrinkableBlockTy("callee", "TB_SIZE")]
    syms = {'TB_SIZE': 256}

    print(call_config_compat_p(caller, callee, syms))

def test_cccp_shr_two():
    "Test with one callee and compatible bounds on caller"
    
    caller = ShrinkableBlockTy("caller", "TB_SIZE_1")
    callee = [ShrinkableBlockTy("callee", "TB_SIZE_2")]
    syms = {'TB_SIZE_1': 256, 'TB_SIZE_2': 512}

    print(call_config_compat_p(caller, callee, syms))

def test_cccp_fix_one():
    "Test with one callee and fixed bounds on caller"
    
    caller = ShrinkableBlockTy("caller", "TB_SIZE_1")
    callee = [FixedBlockTy("callee", "TB_SIZE_2")]
    syms = {'TB_SIZE_1': 512, 'TB_SIZE_2': 256}

    print(call_config_compat_p(caller, callee, syms))

def test_cccp_fix_one_2():
    "Test with one callee and fixed bounds on caller"
    
    caller = ShrinkableBlockTy("caller", "TB_SIZE_1")
    callee = [FixedBlockTy("callee", "TB_SIZE_2")]
    syms = {'TB_SIZE_1': 256, 'TB_SIZE_2': 512}

    print(call_config_compat_p(caller, callee, syms)) # should be false

def test_cccp_elastic_one():
    "Test with one callee and fixed bounds on caller"
    
    caller = ElasticBlockTy("caller", None)
    callee = [ElasticBlockTy("callee", None)]
    syms = {}

    print(call_config_compat_p(caller, callee, syms)) # should be false


if __name__ == "__main__":
    test_cccp_shr_one()
    test_cccp_shr_two()
    test_cccp_fix_one()
    test_cccp_fix_one_2()
    test_cccp_elastic_one()
    #print PyASTSymbolicEval.symbolic_eval("1 + 2", {})
    #syms = {'X': 1, 'Y': 2, 'Z': 'X + Y', 'D': 'Z + A', 'A': 'X * Z'}
    #print syms
    #print build_constants_table(syms)
