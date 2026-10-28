import cgen 
import gg.types

# TODO: Overhaul this!

class IndexVarMixin(object):
    def copy_ndxvar(self, ndxvar):
        self.var_name = ndxvar.var_name
        self.var_type = ndxvar.var_type
        self.increment = ndxvar.increment
        self.offset = ndxvar.offset

        #TODO: pos var should also be an index variable
        self.pos_var_name = ndxvar.pos_var_name
        self.gen_pos_var = ndxvar.gen_pos_var
        self.pos_var_is_comb_offset = ndxvar.pos_var_is_comb_offset
        self.iterator = ndxvar.iterator        



class Index(IndexVarMixin):
    """ Represents the index variable of a loop over an iterator.

     Traverse a portion of the iterator space."""

    def __init__(self, iter_var, iterator, offset = None, increment = None):
        self.iterator = iterator
        self.var_name = iter_var
        self.var_type = self.iterator.iter_type()
        self.increment = "1" if not increment else increment
        self.offset = "0" if not offset else offset

        #TODO: pos var should also be an index variable
        self.pos_var_name = self.var_name + "_pos"
        self.gen_pos_var = False
        self.pos_var_is_comb_offset = False

    def decls(self):
        out = []
        out.append(cgen.Statement("%s %s_end" % 
                                  (self.var_type, self.var_name)))
        return out

    def pre_loop_code(self):
        out = []
        out.append(cgen.Statement(("%s_end = %s" % (self.var_name, 
                                                    self.iterator.end()))))

        return out

    def pos_var_init(self):
        if self.gen_pos_var:
            return "%s = 0" % (self.pos_var_name,)
        else:
            return None

    def pos_var_update(self):
        if self.gen_pos_var:
            return "%s++" % (self.pos_var_name,)
        else:
            return ""

    def loop_init(self):
        l1 = "%s %s = %s + %s" % (self.var_type,
                                  self.var_name,
                                  self.iterator.start(),
                                  self.offset)

        if self.gen_pos_var:
            return cgen.Line("%s, %s" % (l1, self.pos_var_init()))
        else:
            return cgen.Line("%s" % (l1))

    def loop_cond(self):
        return cgen.Line("%s < %s_end" % (self.var_name,
                                      self.var_name))
    

    def loop_update(self):
        u = []
        if self.gen_pos_var: u.append(self.pos_var_update())

        u.append("%s += %s" % (self.var_name, self.increment))

        return cgen.Line(", ".join(u))


class ZeroIndex(object):
    def __init__(self, iterable):
        self.iterable = iterable
        self.var_name = self.iterable.iter_var
        self.var_type = self.iterable.iter_type()
        
    def decls(self):
        out = []
        out.append(cgen.Statement("%s %s_size" % 
                                  (self.var_type, self.var_name)))

        out.append(cgen.Statement("%s %s" % (self.var_type, self.var_name)))
        return out

    def pre_loop_code(self):
        out = []
        out.append(cgen.Statement(("%s = %s" % (self.var_name, 
                                                self.iterable.start()))))

        out.append(cgen.Statement(("%s_size = %s" % (self.var_name, 
                                                     self.iterable.size()))))

        return out

    def loop_init(self):
        return cgen.Line("%s %s_ = 0" % (self.var_type, self.var_name))

    def loop_cond(self):
        return cgen.Line("%s_ < %s_size" % (self.var_name, self.var_name))

    def loop_update(self):
        return cgen.Line("%s++, %s_++" % (self.var_name, self.var_name))


class OffsetIndex(object):
    def __init__(self, iterable):
        self.iterable = iterable
        self.var_name = self.iterable.iter_var
        self.var_type = self.iterable.iter_type()
        self.offset_var = ""
        self.increment = "1"
        # iterable must be an offset iterable?

    def decls(self):
        out = []
        out.append(cgen.Statement("%s %s_size" % 
                                  (self.var_type, self.var_name)))

        return out

    def pre_loop_code(self):
        out = []
        out.append(cgen.Statement(("%s_size = %s" % (self.var_name, 
                                                     self.iterable.size()))))

        return out

    def loop_init(self):
        return cgen.Line("%s %s = %s + %s" % (self.var_type, self.var_name, 
                                              self.iterable.start(),
                                              self.offset_var))

    def loop_cond(self):
        return cgen.Line("%s < %s_size" % (self.var_name, self.var_name))

    def loop_update(self):
        return cgen.Line("%s += %s" % (self.var_name,
                                     self.increment))

class StretchIndex(object):
    def __init__(self, iterable):
        self.iterable = iterable
        self.var_name = self.iterable.iter_var
        self.var_type = self.iterable.iter_type()
        self.offset_var = ""
        self.increment = "1"
        self.mult = ""

        # iterable must be an offset iterable?

    def decls(self):
        out = []
        out.append(cgen.Statement("%s %s" % 
                                  (self.var_type, self.var_name)))

        out.append(cgen.Statement("%s %s_offset" % 
                                  (self.var_type, self.var_name)))

        out.append(cgen.Statement("%s %s_size" % 
                                  (self.var_type, self.var_name)))

        return out

    def pre_loop_code(self):
        out = []
        out.append(cgen.Statement(("%s_size = (%s) * %s" % (self.var_name, 
                                                            self.iterable.size(),
                                                            self.mult))))

        return out

    def loop_init(self):
        return cgen.Line("%s %s_ = %s + %s" % (self.var_type, self.var_name, 
                                               self.iterable.start(),
                                               self.offset_var))

    def loop_cond(self):
        return cgen.Line("%s_ < %s_size" % (self.var_name, self.var_name))

    def loop_update(self):
        return cgen.Line("%s_ += %s" % (self.var_name,
                                        self.increment))

    def pre_body_code(self):
        out = []
        out.append(cgen.Statement("%s = %s_ / %s" % (self.var_name, self.var_name, self.mult)))
        out.append(cgen.Statement("%s_offset = %s_ %% %s" % (self.var_name, self.var_name, self.mult)))

        return out


class UniformIterator(gg.types.Iterator):
    def __init__(self, iterator, rounding):
        self.rounding = rounding
        self._iterator = iterator

    def start(self):
        return self._iterator.start()

    def end(self):
        return "(%s) + roundup(((%s) - (%s)), (%s))" % (self._iterator.start(),
                                                    self._iterator.end(), 
                                                    self._iterator.start(),
                                                    self.rounding)

    def size(self):
        return "(%s) - (%s) + 1" % (self.end(), self.start())

    def valid_condition(self):
        # TODO
        return "%s < %s" % ("NDXVAR", self._iterator.size())

class UniformIndex(IndexVarMixin):
    def __init__(self, ndxvar, rounding):
        self._ndxvar = ndxvar
        self.copy_ndxvar(self._ndxvar)
        self.iterator = UniformIterator(ndxvar.iterator, rounding)

    def decls(self):
        out = self._ndxvar.decls()

        out.append(cgen.Statement("%s %s_rup" % 
                                  (self.var_type, self.var_name)))

        return out

    def pre_loop_code(self):
        out = self._ndxvar.pre_loop_code()

        out.append(cgen.Statement("%s_rup = (%s)" % (self.var_name, self.iterator.end())))
        
        return out

    def loop_init(self):
        return self._ndxvar.loop_init()

    def loop_cond(self):
        return "%s < %s_rup" % (self._ndxvar.var_name, self._ndxvar.var_name)

    def loop_update(self):
        return self._ndxvar.loop_update()


class BlockedDistribution(IndexVarMixin):
    def __init__(self, ndxvar, tid, threads):
        self.tid = tid
        self.threads = threads
        self._ndxvar = ndxvar
        
        self.copy_ndxvar(self._ndxvar)

        #self.offset = self._ndxvar.offset
        #self.iterator = self._ndxvar.iterator
        #self.var_type = self._ndxvar.var_type
        #self.var_name = self._ndxvar.var_name


    def decls(self):
        out = self._ndxvar.decls()

        out.append(cgen.Statement("%s %s_block_size" % 
                                  (self.var_type, self.var_name)))

        out.append(cgen.Statement("%s %s_block_start" % 
                                  (self.var_type, self.var_name)))

        return out

    def pre_loop_code(self):
        out = self._ndxvar.pre_loop_code()

        # TODO!
        if isinstance(self._ndxvar, UniformIndex):
            out.append(cgen.Statement(("%s_block_size = %s_rup / %s" % (self.var_name, self.var_name, self.threads))))
        else:
            out.append(cgen.Statement(("%s_block_size = %s_end / %s" % (self.var_name, self.var_name, self.threads))))
        
        out.append(cgen.Statement("%s_block_start = (%s + %s) * %s_block_size" % (self.var_name, self.iterator.start(), self.offset, self.var_name)))
        
        return out

    def loop_init(self):
        return cgen.Line("%s %s = %s_block_start" % (self.var_type, self.var_name, self.var_name))

    def loop_cond(self):
        return "%s < (%s_block_start + %s_block_size) && (%s)" % (self.var_name,self.var_name,  self.var_name, self._ndxvar.loop_cond())

    def loop_update(self):
        return cgen.Line("%s++" % (self._ndxvar.var_name,))
