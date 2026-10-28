import gg.types
 
class MeshIterator(gg.types.Iterator):
    def __init__(self, mesh_expr, offset=None, limit=None):
        super(MeshIterator, self).__init__(offset, limit)
        self.mesh = mesh_expr
    
    def iter_type(self):
        return "index_type"
    
    def start(self):
        return self.offset

    def end(self):
        if self.limit:
            return self.limit
        else:
            return "((%s).nelements)" % (self.mesh,)

    def size(self):
        if self.offset != "0" or self.limit:
            return "(%s) - (%s) + 1" % (self.end(), self.start())
        else:
            return "((%s).nelements)" % (self.mesh)
         
         
class Mesh(gg.types.DataStructure):
    # TODO: serial methods, coop methods

    def __init__(self, mesh):
        self.mesh = mesh 
        
    def triangles(self, offset=None, limit=None):
        return MeshIterator(self.mesh, offset, limit)

# class MeshElementType(Type):
#     #TODO
#     pass
