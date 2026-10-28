import cgen 
from gg.ndxtrans import *
from gg.types import Iterator
from gg.ast.anno import *

class Node(object):
    def __init__(self):
        self.anno = ASTNodeAnno(clonable = True)
        self.generation = None
        self.number = None
        self.name = None

    def check_gen(self, gen): # more appropriately: set_and_check_gen
        if self.generation is None:
            self.generation = gen

        return self.generation >= gen

    def get_props(self):
        return {}
    
    def set_props(self, props):
        return True
    
    def has_anno(self, name):
        return hasattr(self.anno, name)

    def has_anno2(self, dotted_name):
        dn = dotted_name.split(".")

        o = self.anno

        for n in dn:
            if not hasattr(o, n): return False
            o = getattr(o, n)

        return True

    def clone(self):  
        "Returns a clone of this object"
        assert False, self.__class__.__name__

    def _init_clone(self, source):
        "Initialize the clone's non-syntactic attributes"

        self.anno = source.anno.clone_top()
        return self

class Stmt(Node):
    def __init__(self):
        super(Stmt, self).__init__()

class Expr(Node):
    def __init__(self):
        super(Expr, self).__init__()

class Block(Stmt):
    def __init__(self, stmts):
        super(Block, self).__init__()

        if isinstance(stmts, Block):
            # this happens because of the need to differentiate the
            # "UI" and the internal compiler, once the AST is
            # automatically generated and the initial AST uses Block
            # everywhere, we can do away with this.

            self.stmts = stmts.stmts
        else:
            self.stmts = stmts

    def syntax_types(self):
        return {'stmts': ('Statements', list)}

    def clone(self):
        nstmts = [x.clone() for x in self.stmts]
        return Block(nstmts)._init_clone(self)
            
class NOP(Stmt):
    def clone(self):
        return NOP()._init_clone(self)

class Names(Stmt):
    def __init__(self, names):
        super(Names, self).__init__()
        self.names = names

    def symbols(self):
        return [(n, '#define', {'is_builtin': True}) for n in self.names]

    def clone(self):
        return Names(self.names)._init_clone(self)

class Kernel(Node):
    """
    Kernel name(args)
      stmts

    Defines a kernel named *name* that accepts *params*.

    A kernel may iterate over a worklist and push and pop to it.

    Implementation details:

    Host kernels compile to CPU functions.
    """
    def __init__(self, name, params, stmts, host=None, ret_type = "void", device=None, _emit = True):
        super(Kernel, self).__init__()
        self.name = name
        self.args = params
        
        if isinstance(self.args, tuple): # TODO: syntax error?
            self.args = list(self.args)

        self.stmts = Block(stmts)
        self.host = host
        self.device = device
        self.ret_type = "void" if not (host or device) else ret_type
        self._emit = _emit

    def syntax_types(self):
        return {'name': ('Kernel name', str),
                'stmts': ('Statements', Block)}

    def syntax_check(self, compiler):
        out = [compiler.check(self.name, "Kernel must have a name"),
               compiler.check(all([isinstance(a, tuple) and len(a) == 2 for a in self.args]), "Invalid syntax for parameters (must be '(type, name)')", self.name),
               ]

        return all(out)

    def symbols(self):
        return [(n, t, {'is_param': True}) for t, n  in self.args]

    def clone(self):
        return Kernel(self.name, list(self.args), self.stmts.clone(),
                      self.host, self.ret_type, self.device, self._emit)._init_clone(self)

    def __str__(self):
        return "Kernel/%s" % (self.name,)

class Module(Node):
    def __init__(self, stmts):
        super(Module, self).__init__()
        self.name = "__module__"
        self.stmts = Block(stmts)

    # poor man's import facility
    def get_kernel(self, name):
        for s in self.stmts.stmts:
            if isinstance(s, Kernel) and s.name == name:
                return s

        return None

    def clone(self):
        return Module(self.stmts.clone())._init_clone(self)


class For(Stmt):
    def get_props(self):
        p = {'ndx': self.ndxvar.__class__.__name__,
             'ndxvar': self.ndxvar.var_name}

        if hasattr(self.ndxvar, 'offset_var'):
            p['offset_var'] = self.ndxvar.offset_var

        return p

    def set_props(self, props):
        n2c = {'Index': Index, 'ZeroIndex': ZeroIndex,
               'OffsetIndex': OffsetIndex, 'StretchIndex': StretchIndex}

        if props['ndx'] != self.ndxvar.__class__.__name__:
            self.ndxvar = n2c[props['ndx']](self.iterable)


        if 'offset_var' in props:
            self.ndxvar.offset_var = props['offset_var']

        self.props = props

        return True
        
    def __init__(self, ndxvar, iterator, stmts, name = None):
        super(For, self).__init__()
        self.iterator = iterator
        self.stmts = Block(stmts)
        self.ndxvar_name = ndxvar
        self.ndxvar = Index(ndxvar, iterator)
        #TODO: have a walk and call empty set_props?
        self.props = {}
        self.name = name

    def syntax_types(self):
        return {'ndxvar_name': ('Index variable', str),
                'stmts': ('Statements', Block),
                'iterator': ('Iterator', Iterator)}

    def symbols(self):
        o = [(self.ndxvar_name, 'index_type', {})] 

        if self.ndxvar.gen_pos_var:
            #TODO: handle this nicer...
            o.append((self.ndxvar.pos_var_name, 'index_type', {'is_comb_offset': self.ndxvar.pos_var_is_comb_offset }))

        return o

    def _init_clone(self, src):
        x = super(For, self)._init_clone(src)
        if src.ndxvar.gen_pos_var:
            x.ndxvar.gen_pos_var = True
            x.ndxvar.pos_var_is_comb_offset = src.ndxvar.pos_var_is_comb_offset

        return x

    def clone(self):
        return For(self.ndxvar_name, self.iterator.clone(), self.stmts.clone())._init_clone(self)


class CFor(Stmt):    
    def __init__(self, init, cond, update, stmts, name = None):
        super(CFor, self).__init__()

        if isinstance(init, str) or isinstance(init, CDecl):
            init = [init]

        if isinstance(update, str):
            update = [update]
            
        self.init = init # array
        self.cond = cond
        self.update = update # array
        self.stmts = Block(stmts)  
        self.name = name

    def syntax_types(self):
        return {'init': ('Initialization', list),
                'cond': ('Condition', str),
                'update': ('Update', list),
                'stmts': ('Statements', Block)}

    def symbols(self):
        out = []
        for i in self.init:
            if isinstance(i, CDecl):
                out += i.symbols()

        return out

    def c_expr(self):
        #TODO: handle init expressions

        return [('cond', self.cond), ('update', self.update)]

    def clone(self):
        out = []
        for i in self.init:
            if isinstance(i, CDecl):
                out.append(i.clone())
            else:
                out.append(i)

        return CFor(out, self.cond, list(self.update), self.stmts.clone())._init_clone(self)

class While(Stmt):
    def __init__(self, cond, stmts, name = None):
        super(While, self).__init__()

        self.cond = cond
        self.stmts = Block(stmts)
        self.name = name

    def syntax_types(self):
        return {'stmts': ('Statements', Block)}

    def syntax_check(self, compiler):
        return all([compiler.check(self.cond, "Condition must not be empty (currently '%s')" % (self.cond,), "While"),
                    ])

    def c_expr(self):
        return [('cond', self.cond)]

    def clone(self):
        return While(self.cond, self.stmts.clone())._init_clone(self)

    def __str__(self):
        return "While(%s)" % (self.cond,)

class Assign(Stmt):
    def __init__(self, lhs, rhs):
        super(Assign, self).__init__()

        self.lhs = lhs
        self.rhs = rhs

    def syntax_types(self):
        return {'lhs': ('LHS', str), 'rhs': ('RHS', Expr)} 

    def syntax_check(self):
        return all([compiler.check(self.lhs, "LHS cannot be empty (currently '%s')" % (self.lhs,), "Assign")])

    def c_expr(self):
        return [('lhs', self.lhs)] + self.rhs.c_expr()

    def clone(self):
        return Assign(self.lhs, self.rhs.clone())._init_clone(self)
                    
class DoWhile(Stmt):
    def __init__(self, cond, stmts, name = None):
        super(DoWhile, self).__init__()

        self.cond = cond
        self.stmts = Block(stmts)
        self.name = name

    def syntax_types(self):
        return {'stmts': ('Statements', Block)}

    def syntax_check(self, compiler):
        return all([compiler.check(self.cond, "Condition must not be empty (currently '%s')" % (self.cond,), "DoWhile")])

    def c_expr(self):
        return [('cond', self.cond)]

    def clone(self):
        return DoWhile(self.cond, self.stmts.clone())._init_clone(self)

class Retry(Stmt):
    def __init__(self, args = None, merge = False):
        super(Retry, self).__init__()

        self.args = args
        self.merge = merge

    def syntax_types(self):
        return {'args': ('argument', str), 'merge': ('merge', bool)} 

    def c_expr(self):
        return [('args', self.args)]

    def clone(self):
        return Retry(self.args)._init_clone(self)


class Respawn(Retry):
    def __init__(self, args = None):
        super(Respawn, self).__init__()
        self.args = args

    def syntax_types(self):
        return {'args': ('argument', str)} 

    def c_expr(self):
        return [('args', self.args)]

    def clone(self):
        return Respawn(self.args)._init_clone(self)

class ForAll(For):
    """ForAll(var In iterator)
      stmts
      
   Iterate over elements provided by the iterator. ForAll declares
   that *stmts* can be executed in parallel.

   A top-level ForAll as the first statement in a Kernel signifies
   that the kernel may be compiled for parallel execution with each
   iteration executed in a separate logical thread. Statements before
   this ForAll statement are executed in every logical thread before
   *stmts*.

   Multiple top-level ForAll statements are supported in the kernel.

   Nested ForAll statements are deemed to spawn "sub-threads" and have
   restricted write access to thread-local variables outside the
   nested ForAll.
   """

    def __str__(self):
        return "ForAll/%s" % (self.ndxvar_name)

    def _init_clone(self, src):
        x = super(ForAll, self)._init_clone(src)
        if src.ndxvar.gen_pos_var:
            x.ndxvar.gen_pos_var = True
            x.ndxvar.pos_var_is_comb_offset = src.ndxvar.pos_var_is_comb_offset

        return x
        
    def clone(self):
        return ForAll(self.ndxvar_name, self.iterator.clone(), self.stmts.clone())._init_clone(self)
    
class Atomic(Stmt):
    """ Atomic(object) 
      stmts
    [Else
      fail-stmts]

    Acquire lock *object* and execute *stmts*, releasing lock before
    executing the next statement.

    If an Else clause is provided, execute *fail-stmts* if acquiring
    the lock failed.
    
    Control flow inside an atomic may not "break out of the Atomic" --
    break, continue (on loops outside the Atomic) and return are
    forbidden.
    """
    def __init__(self, lock, lockndx, stmts, fail_stmts, name = None):
        super(Atomic, self).__init__()

        self.lock = lock
        self.lockndx = lockndx # for LockArray
        self.stmts = Block(stmts)
        self.fail_stmts = Block(fail_stmts) # failed to acquire lock
        self.name = name

    def syntax_types(self):
        return {'lock': ('Lock', str),
                'lockndx': ('Lock index', str),
                'stmts': ('Lock acquired statements', Block),
                'fail_stmts': ('Lock failed statements', Block)}

    def c_expr(self):
        return [('lock', self.lock), ('lockndx', self.lockndx)]

    def clone(self):
        return Atomic(self.lock, self.lockndx, self.stmts.clone(), 
                      self.fail_stmts.clone())._init_clone(self)

class ExclusiveArrayIterator(Expr):
    """Iterator over Array for use in Exclusive"""
    def __init__(self, array, start = "0", end = None, step = "1"):
        self.array = array
        self.start = start
        self.end = end
        self.step = step

    def syntax_types(self):
        o = {'array': ('Array', str),
             'start': ('Start', str),
             'step': ('Step', str)}
        
        if end is not None:
            o['end'] = ('End', str)

        return o

    def c_expr(self):
        out = [('array', self.array), ('start', self.start), 
               ('step', self.step)]

        if end is not None:
            out.append(('end', self.end))

        return out

    def clone(self):
        return ExclusiveArrayIterator(self.array, self.start,
                                      self.end, self.step)

class Exclusive(Stmt):
    """ Exclusive(objects)
        stmts
    [Else
        fail-stmts]

    objects is a tuple of ("object", [(N, locks), ...])  with *N* and
    *locks* indicating the *N* locks to be obtained on *object*.

    Exclusive will attempt to obtain the specified locks, and on
    success execute *stmts*. If conflicts are encountered, one of
    conflicting threads is guaranteed to make forward progress.

    Exclusive can abandon attempting to acquire the locks and
    execution will continue at the next statement. However, if the
    Else clause is supplied, execution continues with *fail-stmts*.

    By definition, Exclusive always succeeds when asked to obtain zero
    locks.


    Implementation-dependent restrictions:

    Exclusive must be control-dependent on the top-level ForAll.

    Exclusives cannot be nested. 

    TODO: Locking over multiple objects?
    """
    
    
    def __init__(self, obj_n_to_lock, stmts, fail_stmts, name = None):
        # obj_n_to_lock is a (obj, (n1, to_lock1), (n2, to_lock2)) etc.
        super(Exclusive, self).__init__()

        self.to_lock = obj_n_to_lock
        self.stmts = Block(stmts)
        self.fail_stmts = Block(fail_stmts)
        self.name = name

    @staticmethod
    def setup(size, kernel):
        return MethodInvocation(None, "setup", "Exclusive", [size, kernel])

    def syntax_types(self):
        return {'stmts': ('Lock acquired statements', Block),
                'fail_stmts': ('Lock failed statements', Block),
                'to_lock': ('Objects to lock', list)}

    def check_syntax(self, compiler):
        def valid_to_lock_member(xx):
            return (isinstance(x, tuple) and len(x) == 2 and isinstance(x[1], list)) or (isinstance(x, ExclusiveArrayIterator))

        out = []
        if all([valid_to_lock_member(x) for x in self.to_lock]):
            for obj, portions in self.to_lock:
                out.append(compiler.check(isinstance(obj, str), "Object to lock must be a scalar (currently %s)" % (obj,), "Exclusive"))

                if not isinstance(portions, ExclusiveArrayIterator):
                    for l, a in portions:
                        out.append(compiler.check(isinstance(l, str), "Size of portion must be a scalar (currently %s)" % (l,), "Exclusive"))
                        out.append(compiler.check(isinstance(a, str), "Array in portion must be a scalar (currently %s)" % (a,), "Exclusive"))
                else:
                    # TODO: check syntax of ExclusiveArrayIterator
                    pass

            return all(out)
        else:
            return compiler.check(False, "to_lock must be [(obj_to_lock, [(size, array), ...]), ...] (currently %s)" % (self.to_lock), "Exclusive") 

    def c_expr(self):
        out = []
        for i, (obj, portions) in enumerate(self.to_lock):
            name = 'to_lock_obj[%d]' % i
            out.append((name, obj))
            for j, portion in enumerate(portions):
                if isinstance(portion, tuple):
                    l, a = portion
                    out.append((name + "[%d].length" % (j,), l))
                    out.append((name + "[%d].array" % (j,), a))
                else:
                    # TODO: ExclusiveArrayIterator
                    pass

        return out

    def clone(self):
        return Exclusive(self.to_lock, self.stmts.clone(),
                         self.fail_stmts.clone())._init_clone(self)

class CBlock(Stmt):
    def __init__(self, stmts, parse = True, decl = False, _scope = "all"): 
        super(CBlock, self).__init__()

        if isinstance(stmts, str):
            stmts = [stmts]

        self.stmts = stmts
        self.parse = parse
        self.decl = decl
        self._scope = _scope

    def syntax_types(self):
        return {'stmts': ('Statements', list),
                'parse': ('parse attribute', bool),
                'decl': ('decl attribute', bool)}
               
    def c_expr(self):
        return [('stmts', self.stmts)]

    def symbols(self):
        out = []
        for s in self.stmts:
            if isinstance(s, cgen.Define):
                out.append((s.symbol, "#define", {'cval': s.value})) # type for now

        return out

    def clone(self):
        return CBlock(list(self.stmts), self.parse, self.decl, self._scope)._init_clone(self)

class CExpr(Expr):
    def __init__(self, expr, parse = True):
        super(CExpr, self).__init__()

        self.expr = expr
        self.parse = parse

    def syntax_types(self):
        return {'expr': ('Expression', str),
                'parse': ('parse attribute', bool)}

    def c_expr(self):
        return [('expr', self.expr)]
        
    def clone(self):
        return CExpr(self.expr, self.decl)._init_clone(self)

class CDecl(CBlock):
    def __init__(self, decls, dont_move = False, addr_gpu = False):
        if isinstance(decls, tuple) and len(decls) == 3 and not isinstance(decls[0], tuple):
            decls = [decls]

        assert not isinstance(decls, str)

        self.decls = decls
        self.symbol_flags = {}

        if addr_gpu:
            self.addr_space = "gpu"
        else:
            self.addr_space = "cpu"

        self.dont_move = dont_move # because of typedefs
        stmts = [("%s %s %s" % (t, n, i) for t, n, i in decls)]

        super(CDecl, self).__init__(stmts, parse=False, decl=True)

        for n, t, f in self.symbols():
            f['addr_space'] = self.addr_space
            self.symbol_flags[n] = f

    def syntax_types(self):
        return {'decls': ('Declarations', list), 'dont_move': ('dont_move', bool)}

    def syntax_check(self, compiler):
        return all([compiler.check(isinstance(d, tuple) and len(d) == 3 and all([isinstance(x, str) for x in d]), 
                                   "Incorrect declaration, must be (type, variable, initializer), currently ('%s')" % (d,), "CDecl") for d in self.decls])
    
    def c_expr(self):
        return [(n, "%s %s %s" % (t, n, i)) for (t, n, i) in self.decls]

    def set_symbol_flags(self, flags):
        self.symbol_flags = flags

    def symbols(self):
        def rm_array(x):
            p = x.find("[")
            if p >= 0:                
                n = x[:p]
                f = self.symbol_flags.get(n, {})
                f['is_array'] = True
                self.symbol_flags[n] = f
                
                return n
            else:
                return x

        tmp = {}
        for t, n, i in self.decls:
            tmp[n] = rm_array(n)

        return [(tmp[n], t, self.symbol_flags.get(tmp[n], {})) 
                for t, n, i in self.decls]

    def _init_clone(self, src):
        x = super(CDecl, self)._init_clone(src)

        x.set_symbol_flags(src.symbol_flags.copy()) # flags are primitive

        return x

    def clone(self):
        return CDecl(list(self.decls), self.dont_move, self.addr_space == "gpu")._init_clone(self)

def CDeclGlobal(*args, **kwargs):
    x = CDecl(*args, **kwargs)

    for n, t, f in x.symbols():
        f['is_global'] = True
        x.symbol_flags[n] = f

    return x

class ReturnFromParallelFor(Stmt):
    """ ReduceAndReturn value

    Sets value as the return value of the logical thread and
    terminates execution of the thread.

    If executed in a nested ForAll, sets the value of the logical
    thread by reduction and terminates execution of the subthread.

    Return values from all logical threads are reduced as specified at
    the invocation point.
    """
    def __init__(self, value):
        super(ReturnFromParallelFor, self).__init__()

        self.value = value

    def syntax_types(self):
        return {'value': ('Return value', str)}

    def c_expr(self):
        return [('value', self.value)]

    def clone(self):
        return ReturnFromParallelFor(self.value)._init_clone(self)

class If(Stmt):
    def __init__(self, cond, true_stmts, false_stmts = None, name = None):
        super(If, self).__init__()

        self.cond = cond
        self.true_stmts = Block(true_stmts)
        self.false_stmts = Block([] if false_stmts is None else false_stmts)
        self.name = name

    def syntax_types(self):
        return {'cond': ('Condition', str),
                'true_stmts': ('True statements', Block),
                'false_stmts': ('False statements', Block),
                }

    def c_expr(self):
        return [('cond', self.cond)]

    #def blocks(self):
    #    return [('st_true_stmts', self.true_stmts), 
    #            ('st_false_stmts', self.false_stmts)]

    def __str__(self):
        return "If/%s" % (self.cond,)

    def clone(self):
        return If(self.cond, self.true_stmts.clone(), self.false_stmts.clone())._init_clone(self)

class Invoke(Stmt):
    """ Invoke [Any|All] kernel(args)

    Executes *kernel* and reduces the return values of the kernel
    using the optional reduction operator. 

    Currently only Any and All are supported as reduction
    operators. Any returns true if any of the logical threads returned
    true, while All returns true only if the logical threads returned
    true.

    Invoke does *not* create a worklist. Invoking a kernel that uses a
    worklist is not permitted unless Invoke is executed inside a Pipe.

    Implementation Specific Details:

    Invoke is really an expression and not a statement. The current
    implementation needs to handle this.

    Other reduction operators that may be supported in the future
    (e.g. Majority, Sum, etc.)
    """
    def __init__(self, kernel, args, _alt = None, _noadvance = False, name = None):
        super(Invoke, self).__init__()

        self.kernel = kernel
        if isinstance(args, (list, tuple)):
            self.args = [str(s) for s in args]
        else:
            self.args = args
        self.alt = _alt # property of a kernel?
        self._noadvance = _noadvance
        self.name = name

    def syntax_types(self):
        return {'kernel': ('Kernel name', str),
                'args': ('Kernel arguments', list),
                }

    def c_expr(self):
        return [('args', self.args)]

    def clone(self):
        return Invoke(self.kernel, list(self.args), 
                      self.alt, self._noadvance)._init_clone(self)

class Iterate(Stmt):
    """ Iterate [Until|While Any|All [AndCond | OrCond]] kernel (args) [WorklistInit size, iter-expr]
        stmts

    Repeat execution of *kernel* until specified termination condition
    on the return value of the kernel is reached. Execute *stmts*
    after every invocation. The WorklistInit clause specifies the size
    and initial values of the worklist used by the kernel.

    A termination condition can be implicit in which case the
    iteration stops when the worklist used by the kernel is depleted.
    It is an error to invoke a kernel with an implicit condition when
    it does not use a worklist.  (TODO: Is this is a while () or a do
    {} while() )

    If a termination condition is provided, execute the kernel until
    the condition is met OR the worklist (if one is used by the
    kernel) is depleted.

    Iterate will create a fresh worklist when run standalone and
    initialize it using the values in the Initial clause. It will
    inherit the worklist created by Pipe if one is available, in which
    case the Initial clause will be ignored.

    A Iterate with an implicit termination condition is forbidden
    inside a Pipe [TODO: in Pipe Once?].
    """

    def clone(self):
        return Iterate("UNTIL" if self.until else "WHILE", 
                       self.condition, self.kernel, list(self.kernel_args),
                       worklist_init = self.worklist_init.clone() if self.worklist_init else None,
                       stmts = self.stmts.clone(),
                       extra_cond = self.extra_cond,
                       _alt = self.alt, 
                       _sign = self._sign, 
                       _call = self._call)._init_clone(self)

    def __init__(self, while_until, condition, kernel, kernel_args, 
                 worklist_init = None, stmts = None, extra_cond = None, name = None,
                 _alt = None, _sign = None, _call = None):

        super(Iterate, self).__init__()

        self.until = while_until.upper() == "UNTIL"
        self.worklist_init = None

        if condition.upper() in ('ALL', 'ANY'):
            self.condition = condition.upper()
            self.worklist = None
            assert worklist_init is None, "worklist_init provided for non-WL Iterate" # this is a syntax error
        elif condition[:2].upper() == "WL": # why the :2?
            self.condition = "WL"
            #assert worklist_init is not None, this should be caught by a semantic checker pass
            self.worklist_init = worklist_init
        else:
            assert False, "Unknown condition %s " % (condition,)

        self.extra_cond = extra_cond
        if extra_cond: # ('&&', 'cond') or ('||', 'cond')
            assert extra_cond[0] in ('&&', '||')

        self.kernel = kernel
        self.kernel_args = [str(s) for s in kernel_args]
        self.stmts = Block(stmts if stmts is not None else [])
        self.alt = _alt
        self._sign = _sign
        self._call = _call
        self.name = name

    def syntax_types(self):
        x = {'kernel': ('Kernel name', str),
                'kernel_args': ('Kernel arguments', list),
                'stmts': ('Statements', Block),
             }
        if self.worklist_init is not None:
            x.update({'worklist_init': ('Worklist Init', WorklistInitializer)})

        return x

    def c_expr(self):
        out = [('args', self.kernel_args)]
        if self.extra_cond:
            out.append(('extra_cond', self.extra_cond[1]))

        if self.condition == "WL" and self.worklist_init:
            out += self.worklist_init.c_expr()

        return out

    #def blocks(self):
    #    return [('st_stmts', self.stmts)]

    def symbols(self):
        return [('wl', 'PipeContext',  {'is_cgen': True})]

class MethodInvocation(Expr):
    def __init__(self, obj, method, obj_type, args, name = None):
        super(MethodInvocation, self).__init__()
        self.obj = obj
        self.method = method
        self.obj_type = obj_type
        self.args = [str(s) for s in args]
        self.name = name

    def c_expr(self):
        return [('args', self.args)]

    def __str__(self):
        return "%s.%s" % (self.obj, self.method)

    def clone(self):
        # TODO: copy method annotations?

        return MethodInvocation(self.obj, self.method, 
                                self.obj_type,
                                list(self.args))._init_clone(self)

# note that we may be able to conservatively auto-determine barrier
# type depending on writes

class HierarchicalBarrier(Stmt):
    """Hierarchical barrier, 0 is global (all-threads),
       others are (right now) backend specific.

       Named barriers are not yet supported."""

    def __init__(self, level=0):
        super(HierarchicalBarrier, self).__init__()
        self.level = level

    def clone(self):
        return HierarchicalBarrier(self.level)._init_clone(self)

class GlobalBarrier(HierarchicalBarrier):
    """ GlobalBarrierSync

    Executes a barrier among all *running* logical threads. This is
    the subset of logical threads that are executing concurrently.

    Implementation-specific Details:

    GlobalBarriers must be setup using setup method indicating the
    function which uses global barriers. This is a temporary
    workaround for compiler limitations and will be done away with.
    """
    def __init__(self):
        super(GlobalBarrier, self).__init__()

    def sync(self):
        return Uniform(MethodInvocation(self, "sync", "GlobalBarrier", []), uniform = False, place_uniform = True, place_level = self.level)

    # TODO: temporary
    def setup(self, kernel):
        return MethodInvocation(self, "setup", "GlobalBarrier", [kernel])

    def clone(self):
        return GlobalBarrier()._init_clone(self)

class LocalBarrier(HierarchicalBarrier):
    """Local is a misnomer, this is a thread-block level barrier"""

    def __init__(self):
        super(LocalBarrier, self).__init__(1)

    def sync(self):
        return Uniform(MethodInvocation(self, "sync", "LocalBarrier", []), uniform = False, place_uniform = True, place_level = self.level)

    def clone(self):
        return LocalBarrier()._init_clone(self)

class WorklistInitializer(object):
    def __init__(self, size, initial = None):
        self.size = size
        self.initial = [] if initial is None else initial

        # TODO: syntax check

    def c_expr(self):
        return [('size', self.size), ('initial', self.initial)]

    def _init_clone(self, src):
        return self

    def clone(self):
        return WorklistInitializer(self.size, list(self.initial))._init_clone(self)

class WorklistInitializerFromArray(WorklistInitializer):
    def __init__(self, size, array, array_size):
        self.size = size
        self.array = array
        self.array_size = array_size

        # TODO: syntax check

    def c_expr(self):
        return [('size', self.size), ('array', self.array), ('size', self.size)]

    def _init_clone(self, src):
        return self

    def clone(self):
        return WorklistInitializerFromArray(self.size, self.array, self.array_size)._init_clone(self)


WLInit = WorklistInitializer
WLInitFromArray = WorklistInitializerFromArray

class Pipe(Stmt):
    """
    Pipe [Once] [WLInit size[, iter-expr]]
       stmts

    A top-level Pipe creates worklist, initialized by the optional
    Initial clause, that is inherited by all Invoke, Iterates and nested
    Pipes in stmts.

    A looping Pipe (i.e. without Once) executes *stmts* until the
    worklist it has created is depleted. The *stmts* are executed at
    least once (i.e. it has do() {} while() semantics)

    A Pipe Once only executes *stmts* once and serves primarily as a
    communication construct.

    Within a pipe, the output worklist of an invocation (i.e. pushed
    values) are made available to the input worklist of the next
    invocation (i.e. values returned from pop).

    Nested Pipes do not create a worklist.
    
    *Stmts* may not break out of outer loops, though support for
     Break, Continue, etc. may be grafted onto Pipes.

    TODO: Host kernel semantics with pipes.
    """
    def clone(self):
        return Pipe(self.stmts.clone(),
                    wlinit = self.init.clone() if self.init else None,
                    once=self.once, _sign =self._sign, _call = self._call)._init_clone(self)

    def __init__(self, stmts, wlinit=None, once=False, name = None, _sign = None, _call = None):
        super(Pipe, self).__init__()

        # size is only optional for nested Pipes
        self.stmts = Block(stmts)
        self.once = once # == !loop which is default
        self.init = wlinit # ideally, inferred?
        self._sign = _sign
        self._call = _call 
        self.name = name

    def syntax_types(self):
        return {'once': ('Once', bool),
                'stmts': ('Statements', Block)}

    def c_expr(self):
        if self.init:
            return self.init.c_expr()

        return []

    #def blocks(self):
    #    return [('st_stmts', self.stmts)]

    def symbols(self):
        return [('pipe', 'PipeContext',  {'is_cgen': True})]

def CondC(cond, stmt, else_stmt = None): 
    """Conditional Compilation -- returns stmt if cond is True else returns else_stmt which is NOP if not specified."""

    if cond:
        return stmt
    else:
        if else_stmt is not None:
            return else_stmt
        else:
            if isinstance(stmt, list):
                return [NOP()]
            else:
                return NOP()

def parse_input(inputfile):
    import sys
    #TODO: Generalize this to import from any path
    if "." not in sys.path:
        sys.path.append(".")
    
    inp = __import__(inputfile[:-3]) # remove .py

    return inp.ast

BlockStatements = (Module, Kernel, Block, While, DoWhile, Exclusive, Atomic, If, Pipe, Iterate, ForAll, For, CFor)
LoopStatements = (While, DoWhile, ForAll, For, CFor) # also Pipe, Iterate?, this is a list within the loop
LoopExitStatements = (Retry,)
