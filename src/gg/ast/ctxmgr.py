class WalkerContext(object):
    pass

class CtxManager(object):
    ctx_prop_name = ""

    def get_ctx_prop(self):
        return None

    def init_ctx(self, ctx):
        assert ctx_prop_name is not None
        
        assert not hasattr(ctx, ctx_prop_name), "%s is already defined in context" % (ctx_prop_name,)

        setattr(ctx, ctx_prop_name, self.get_ctx_prop())

    def enter_node_ctx(self, node):
        raise NotImplemented

    def exit_node_ctx(self, node):
        raise NotImplemented


class SymTabCtxMgr(object):
    ctx_prop_name = "symtab"

    def get_ctx_prop(self):
        return Stack()

    def enter_node_ctx(self, node, ctx):
        if isinstance(node, BlockStatements):
            ctx.symtab.push(node.symtab)

    def exit_node_ctx(self, node, ctx):
        if isinstance(node, BlockStatements):
            ctx.symtab.pop()

