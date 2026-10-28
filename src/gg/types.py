class Iterator(object):
    """
   A iterator is provided by a data structure such as Worklist or Graph.

   The iterator is read-only, random-access and of a fixed size.
   """

    def __init__(self, offset=None, limit=None):
        self.offset = "0" if offset is None else offset
        self.limit = limit

    def iter_type(self):
        return "index_type"

    def start(self):
        return self.offset

    def end(self):
        pass

    def size(self):
        return "(%s) - (%s)" % (self.end(), self.start())

    def clone(self):
        # TODO
        return self

class RangeIterator(Iterator):
    def __init__(self, end, start = "0", increment = "1", ty = "int"):
        self.limit = end
        self.offset = start
        self.increment = increment
        self.ty = ty

    def iter_type(self):
        return self.ty

    def start(self):
        return self.offset

    def end(self):
        return self.limit

    def size(self):
        return "(%s) - (%s)" % (self.end(), self.start())

class DataStructure(object):
    serial_methods = {} # user-method -> serial method
    coop_methods = {}   # user-method -> coop method
