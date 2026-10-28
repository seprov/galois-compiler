import gg.passes.instr
import cgen
import re

CID = re.compile('[A-Za-z_][A-Za-z0-9_]*')

def is_lvalue(k, s):
    # simplified matcher, should actually use C parser?
    # will not match (x) for example.

    if CID.match(s) is not None:
        sym =  k.symtab.lookup(s)
        
        if sym:
            return not sym.cval

    return False

def sl_states(k, invc, args, cntvar, mode='save'):
    if not k.has_anno('statesaver'):
        return []

    #print k.anno.statesaver


    out = []
    for s in k.anno.statesaver.state_vars:
        ifargs = ['"%s"' % (k.name,), cntvar, 
                  str(s.argpos),
                  '"%s"' % (k.args[s.argpos][1],)]

        # NOTE: args[s.argpos] is assumed to be either an lvalue or an
        # expression.
        #
        # expressions (i.e. variables forming the expression) are not saved!

        comment = False
        if s.name[0] != '+':
            comment = not is_lvalue(k, args[s.argpos])
            ifargs.append("&(%s)" % (args[s.argpos]),)
            ifargs.append(s.size)
            fn = 'instr_%s_primitive' % (mode,)
        elif s.name == '+NodeData+':
            ifargs[-1] = ifargs[-1] + '"_nd"'
            gvar = args[s.argpos]
            ifargs.append("(%s).node_data" % (gvar,))
            ifargs.append("NULL"); # graph.node_data has no internal CPU copy 
            ifargs.append("sizeof((%s).node_data[0])" % (gvar,)) # will not deference
            ifargs.append("(%s).nnodes" % (gvar))

            fn = 'instr_%s_array' % (mode,)

        if s.addrspace == gg.passes.instr.AS_GPU:
            fn += '_gpu'

        if comment:
            out.append(cgen.Line("// %s(%s)" % (fn, ", ".join(ifargs))))
        else:
            out.append(cgen.Statement("%s(%s)" % (fn, ", ".join(ifargs))))

    shvar = {}
    arinfo = {}

    if invc.has_anno('shvar_anno'):
        shvar = dict(invc.anno.shvar_anno.shared_vars)

    if invc.has_anno('array_info'):
        arinfo = invc.anno.array_info.ainfo
    
    if mode == 'load':
        sh_fn = "cpu_wr_ptr()"
    else:
        sh_fn = "cpu_rd_ptr()"

    for s in k.anno.statesaver.array_vars:
        ifargs = ['"%s"' % (k.name,), cntvar, 
                  str(s.argpos),
                  '"%s"' % (k.args[s.argpos][1],)]

        comment = False
        if s.argpos in shvar:
            v = shvar[s.argpos]
            
            ifargs.append("(%s).%s" % (v, sh_fn))
            ifargs.append("sizeof((%s).%s[0])" % (v, sh_fn)) # will not deference
            ifargs.append("(%s).size()" % (v))

            fn = 'instr_%s_array' % (mode,)
        elif args[s.argpos] in arinfo:
            v = args[s.argpos]
            ifargs.append("(%s)" % (v,))
            ifargs.append("NULL")
            ifargs.append("sizeof((%s)[0])" % (v,)) # will not deference
            ifargs.append("%s" % (arinfo[args[s.argpos]].maxsize))

            fn = 'instr_%s_array_gpu' % (mode,)
        else:
            comment = True
            v = args[s.argpos]
            ifargs.append("(%s)" % (v,))
            ifargs.append("sizeof(*(%s)[0])" % (v,)) # will not deference
            ifargs.append("?")

            fn = 'instr_%s_array_gpu' % (mode,)
        
        if comment:
            out.append(cgen.Line("// %s(%s)" % (fn, ", ".join(ifargs))))
        else:
            out.append(cgen.Statement("%s(%s)" % (fn, ", ".join(ifargs))))


    for s in k.anno.statesaver.unhandled_vars:
        out.append(cgen.Line("// instr_unhandled %s:%s:%s" % (s.name, s.ty, args[s.argpos])))

    return out
    

def savestates(k, invc, args, cntvar):
    return sl_states(k, invc, args, cntvar, 'save')

def loadstates(k, invc, args, cntvar):
    return sl_states(k, invc, args, cntvar, 'load')

def filter(k, argpos, cntvar):
    # note there is no save/load combo for filter. We only save.

    v_name = "_filter_%s" % (k.name,)

    args = ['"%s"' % (k.name), "%s-1" % (cntvar,), str(argpos), '"_filter"']

    args.append("%s.cpu_rd_ptr()" % (v_name))
    args.append("sizeof(unsigned char)")
    args.append("%s.size()" % (v_name,))

    return [cgen.Statement("instr_save_array(%s)" % (", ".join(args)))]

