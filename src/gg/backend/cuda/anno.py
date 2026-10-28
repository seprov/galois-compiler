from gg.ast import ASTNodeAnno, Kernel

# TODO: redo this to properly support multiple-arches or remove support here.

class LaunchBoundsAnno(ASTNodeAnno):
    bounds = None

    def __init__(self, max_threads, min_blocks = None, arch = None, arch_comp = "="):
        assert arch_comp in ("=", "<=", ">=", "!=", "<", ">"), "Unrecognized arch_comp: %s" % (arch_comp,)
        assert arch_comp == "=", "Not supported yet, arch_comp = '%s'" % (arch_comp,)
        # TODO: check arch

        self.bounds = {}

        self.bounds[arch] = (max_threads, min_blocks, arch_comp)

        #TODO: ordering when not using arch_comp == "="?

    def combine(self, other):
        for a in self.bounds:
            mt, mb, comp = self.bounds[a]

            if a in other.bounds:
                omt, omb, ocomp = other.bounds[a]

                assert comp == ocomp

                if mt != omt:
                    mt = "({0}) > ({1}) ? ({0}) : ({1})".format(mt, omt)   # maximize threads 

                if mb is None or omb is None:
                    mb = list(filter([mb, omb]))
                else:
                    if mb != omb:                        
                        # TODO: if mb and omb are numeric constants, this may not be needed
                        mb = "({0}) > ({1}) ? ({0}) : ({1})".format(mb, omb)   # maximize occupancy?

            #TODO: we do not support multiple arches yet
            return LaunchBoundsAnno(mt, mb, a, comp)


def LaunchBounds(node, *args, **kwargs):
    assert isinstance(node, Kernel), "node '%s' is not Kernel" % (node,)

    if not node.has_anno('cuda'):
        node.anno.cuda = ASTNodeAnno()

    if len(args) == 1 and isinstance(args[0], ASTNodeAnno):
        assert len(kwargs) == 0
        node.anno.cuda.launch_bounds = args[0]
    else:
        node.anno.cuda.launch_bounds = LaunchBoundsAnno(*args, **kwargs)

    return node
