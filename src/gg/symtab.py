import gg.ast

class Symbol(object):
    name = ""
    ty = ""    
    param = False
    gl = False

    def __init__(self, name, ty, **kwargs):
        self.name = name
        self.ty = ty
        self.param = kwargs.get('is_param', False)
        self.gl = kwargs.get('is_global', False)
        self.builtin = kwargs.get('is_builtin', False)
        self.cgen = kwargs.get('is_cgen', False) # compiler generated
        self.comb_start = kwargs.get('is_comb_start', False)
        self.comb_offset = kwargs.get('is_comb_offset', False)
        self.array = kwargs.get('is_array', False)
        self.cval = kwargs.get('cval', None)
        self.addr_space = kwargs.get('addr_space', None)

        #TODO: check that kwargs doesn't contain other params

        assert not (self.param and self.gl), "Can't be parameter and global at the same time '%s'" % (name,)

    def __str__(self):
        attrs = []
        if self.param: attrs.append("param")
        if self.gl: attrs.append("global")
        if self.builtin: attrs.append("builtin")
        if self.cgen: attrs.append("cgen")
        if self.comb_start: attrs.append("comb_start")
        if self.comb_offset: attrs.append("comb_offset")
        if self.cval: attrs.append("cval: %s" % (self.cval,))
        if self.addr_space: attrs.append("addr_space: %s" % (self.addr_space,))

        return "%s %s: %s" % (self.name, self.ty, " ".join(attrs))

class SymbolTable(object):
    def __init__(self, node, parent = None):
        self.symbols = {}
        self.children = []
        self.parent = parent
        self.node = node
        self.level = 0

        if self.parent:
            self.parent.children.append(self)
            self.level = self.parent.level + 1

    def lookup(self, name, recurse = True):
        if name in self.symbols:
            return self.symbols[name]

        if recurse and self.parent:
            return self.parent.lookup(name)

        return None

    def add(self, name, ty, **kwargs):
        assert name not in self.symbols, "Duplicate symbol '%s'" % (name,) # TODO

        self.symbols[name] = Symbol(name, ty, **kwargs)
        
    def dump(self, recurse = False):
        print ("  " * self.level) + "SYMBOL TABLE for %s %d" % (str(self.node), self.level)
        for n, s in self.symbols.iteritems():
            print "%s%s" % ("  "*(self.level+1), str(s))
        print

        if recurse:
            for c in self.children:
                c.dump(recurse)

    def get_all_constants(self, recurse = True, out = None):
        if out is None:
            out = {}

        for n, s in self.symbols.iteritems():
            # respect scoping
            if n not in out and s.cval is not None:
                out[n] = s.cval
                
        if recurse and self.parent:
            return self.parent.get_all_constants(recurse, out)

        return out

class STAsDict(object):
    def __init__(self, st, fn = None):
        self.st = st
        self.fn = fn

    def __getitem__(self, key):
        x = self.st.lookup(key)
        if x is None:
            raise KeyError

        if self.fn:
            return self.fn(x)
        
        return x
