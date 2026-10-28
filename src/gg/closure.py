PRIMITIVE = set(['int', 'float', 'double', 'unsigned int', 'bool', 'index_type', 'gfloat_p', 'gint_p', 'clock_t', 'char', 'uint', 'int32_t', 'int16_t', 'unsigned char'])
POD = set(['dim3', 'CSRGraphTy', '+Graph+', 'ApproxBitsetByte', 'Any'])
SADDR_PASS_BY_REF = set(['ApproxBitsetByte']) # note approxbitsetbyte may be able to get away without ref.

class TypeTraits(object):
    def __init__(self, ty):
        self.ty = ty.strip()

    def strip_qualifiers(self):
        self.ty = self.ty.replace('extern ', '') # note the space after the qualifier
        self.ty = self.ty.replace('const ', '')
        self.ty = self.ty.replace('__restrict__ ', '')
        self.ty = self.ty.replace('__restrict__', '') # no space!
        self.ty = self.ty.strip()

    def is_primitive(self):
        return self.ty in PRIMITIVE

    def is_pod(self):
        return self.ty in POD

    def is_ref(self):
        return "&" in self.ty or "*" in self.ty

    def is_shared(self):
        return "Shared<" in self.ty

    def saddr_pass_by_ref(self):
        return self.ty in SADDR_PASS_BY_REF 

    def remove_shared(self):
        f = self.ty.find("<")
        if f >= 0:
            l = self.ty.rfind(">")
            if l >= 0:
                return self.ty[f+1:l]

        assert False

    def remove_ref(self):
        # HACK
        return self.ty.replace('&', '').replace('*','')

    def __str__():
        return self.ty

class SimpleClosure(object):
    variables = None
    ty = None
    init = None
    writes = None

    def __init__(self):
        self.variables = []
        self.ty = {}
        self.init = {}
        self.writes = set()

    def add(self, var, ty, init, writes = False):
        assert var not in self.ty, avr

        self.variables.append(var)
        self.ty[var] = ty
        self.init[var] = init

        if writes:
            self.writes.add(var)

    def to_closure_format(self):
        decls = [(v, (self.ty[v], v)) for v in self.variables]
        init = [(v, self.init[v]) for v in self.variables]
        return (decls, init)
