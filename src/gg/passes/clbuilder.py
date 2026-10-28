import gg.passes
import gg.ast.walkers
from gg.ast.misc.cblocks import ClosureEnvironment
from gg.closure import *
from gg.ast.anno import Closure

class ClosureBuilder(gg.ast.walkers.ASTWalker):
    def build_closure(self, node, daddr_required = True):
        complete, env, r, w = ClosureEnvironment().get_environment_rw(self.compiler, node)
        if complete:
            saddr = SimpleClosure()
            xaddr = SimpleClosure()
            success = True

            for name, sym in env.iteritems():
                ty = TypeTraits(sym.ty)
                ty.strip_qualifiers()

                if ty.is_ref():
                    ty2 = TypeTraits(ty.remove_ref())
                    if ty2.is_primitive():
                        if daddr_required:
                            if sym.addr_space != 'gpu':
                                self.compiler.log.debug('CLBuilder does not support pointer %s %s' % (name, sym.ty))
                                success = False
                            else:
                                self.compiler.log.debug('CLBuilder added pointer %s %s (device addr spce)' % (name, sym.ty))
                                # treat as POD
                                saddr.add(name, ty.ty, name, name in w)
                                xaddr.add(name, ty.ty, name, name in w)

                                success = True
                        else:
                            self.compiler.log.debug('CLBuilder added pointer %s %s, valid on saddr only' % (name, sym.ty))
                            saddr.add(name, ty.ty, name, name in w)
                            xaddr.add(name, ty2.ty, "_xlat(%s)" % (name,), name in w)  # atleast fail fast
                    elif ty2.is_pod():
                        saddr.add(name, ty.ty, name, name in w)
                        xaddr.add(name, ty2.ty, name, name in w)  # when sending PODs, send the entire POD
                    else:
                        self.compiler.log.debug('CLBuilder does not support this ref: %s %s' % (name, sym.ty))
                        success = False
                elif ty.is_shared():
                    if sym.array:
                        self.compiler.log.debug('CLBuilder does not support Shared<%s> arrays: %s %s' % (ty2.ty, name, sym.ty))
                        success = False
                    else:
                        # TODO: check that ty is not an array of Shared<>!
                        ty2 = TypeTraits(ty.remove_shared())
                        if ty2.is_primitive():
                            saddr.add(name, ty.ty + "&", name, name in w)  # send Shared<int> as Shared<int>& on the SADDR
                            suffix = ".gpu_wr_ptr()" # TODO: this is conservative, but can be figured out by scanning args, for example
                            xaddr.add(name, ty2.ty + "*", name + suffix, name in w) 
                        else:
                            self.compiler.log.debug('CLBuilder does not support Shared<%s>: %s %s' % (ty2.ty, name, sym.ty))
                            success = False
                elif ty.is_primitive() or ty.is_pod():
                    written = name in w
                    if ty.saddr_pass_by_ref():
                        saddr.add(name, ty.ty + "&", name, written)
                    else:
                        saddr.add(name, ty.ty, name, written)

                    xaddr.add(name, ty.ty, name, written)
                else:
                    self.compiler.log.warning('Missing type info for CLBuilder: %s %s' % (name, sym.ty))
                    success = False
        else:
            # TODO: incorporate user stuff?
            success = False
            saddr = None
            xaddr = None
                    
        return (success, saddr, xaddr)

    def visit_ForAll(self, node):
        if node.check_gen(self.gen):
            if not node.has_anno('closure') and node.has_anno('closure_hint'):
                success, saddr, xaddr = self.build_closure(node, daddr_required = False)
                sa_decls, sa_init = saddr.to_closure_format()
                xa_decls, xa_init = xaddr.to_closure_format()

                self.compiler.log.debug('CLBuilder success: %s %s %s %s %s %s' % (success, node, sa_decls, sa_init, xa_decls, xa_init)) 
                if success:
                    Closure(node, saddr, xaddr, _user = False)
            else:
                super(ClosureBuilder, self).visit_ForAll(node)

    def visit_Pipe(self, node):
        if node.check_gen(self.gen):
            if not node.has_anno('closure') and node.has_anno('closure_hint'):
                success, saddr, xaddr = self.build_closure(node)
                sa_decls, sa_init = saddr.to_closure_format()
                xa_decls, xa_init = xaddr.to_closure_format()

                self.compiler.log.debug('CLBuilder success: %s %s %s %s %s %s' % (success, node, sa_decls, sa_init, xa_decls, xa_init)) 
                if success:
                    Closure(node, saddr, xaddr, _user = False)
            else:
                super(ClosureBuilder, self).visit_Pipe(node)

    def visit_Iterate(self, node):
        if node.check_gen(self.gen):
            if not node.has_anno('closure') and node.has_anno('closure_hint'):
                success, saddr, xaddr = self.build_closure(node)
                sa_decls, sa_init = saddr.to_closure_format()
                xa_decls, xa_init = xaddr.to_closure_format()

                self.compiler.log.debug('CLBuilder success: %s %s %s %s %s %s' % (success, node, sa_decls, sa_init, xa_decls, xa_init)) 
                if success:
                    self.compiler.log.debug('Adding closure to %s' % (node,))
                    Closure(node, saddr, xaddr, _user = False)
            else:
                super(ClosureBuilder, self).visit_Iterate(node)

class ClosureBuilderPass(gg.passes.Pass):
    depends = set(['RWSetsPass'])
    def run(self, compiler, unit, gen, pm):
        v = ClosureBuilder()
        v.visit3(compiler, unit.ast, gen)
        return True
