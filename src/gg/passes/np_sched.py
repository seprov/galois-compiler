import gg.ast.modifier
from gg.ast import Kernel, CBlock, Block, If, While, CDecl, CFor, LocalBarrier, ForAll, CondC, Assign, MethodInvocation, NOP
from gg.ast.anno import Uniform

TB_Barrier = LocalBarrier

# Each scheduler will set _np.size to 0 if it processes a particular
# item.

def init_cvars(cvars, source):
    out = []
    out.append("assert(%s < __kernel_tb_size)" % (source,))
    for cv in cvars:
        out.append("%s = _np_closure[%s].%s" % (cv, source, cv))

    return CBlock(out)

def get_range_condition(mn, mx, var = "_np.size"):
    
    # both mn and mx are strings
    # "0" is a distinguished value indicating no lower limit
    # "" is a distinguished value indicating no upper limit
    # any other value is treated as a constant
    # the range is [mn, mx) if both are specified

    ll = None
    ul = None

    assert mn != "", "Can't have an empty lower limit"
    assert mx != "0", "Can't have zero as the upper limit"

    if mn != "0":
        ll = mn

    if mx != "":
        ul = mx

    cond = []

    if ll is None:
        cond.append("%s > 0" % (var,))
    else:
        cond.append("%s >= %s" % (var, ll))

    if ul is not None:
        cond.append("%s < %s" % (var, ul))  # note the less-than

    return " && ".join(cond)

class NPLoop(object):
    index_type = None
    index_var = None

    work = None

    comb_present = False
    comb_starts = None
    comb_sym = None
    comb_start_init = None

    closure_present = False
    closure_variables = None

class NPScheduler(object):
    multi_outer = False # this scheduler executes multiple outer loop iterations at the same time

    def __init__(self, range_min, range_max, loop, nsched = 1, offset_bucket = None):
        self.range_min = range_min
        self.range_max = range_max
        self.loop = loop
        self.nsched = nsched  # number of schedulers being created
        self.offset_bucket = offset_bucket # None if not using offset buckets, otherwise index of offset_bucket to use

    def shared_init(self):
        return []

    def pre(self):
        return []

    def sched(self):
        return []

    def post(self):
        return []

class NPFineGrained1(NPScheduler):
    default_min = "0"
    multi_outer = True

    def pre(self):
        l = self.loop

        out = []

        if self.offset_bucket is None:
            out.append(CBlock(["_np.total = _np_mps_total",
                               "_np.offset = _np_mps"]))
        else:
            out.append(CBlock(["_np.total = _np_mps_total.el[%d]" % (self.offset_bucket,),
                               "_np.offset = _np_mps.el[%d]" % (self.offset_bucket,)]))
                   

        if l.comb_present:
            for s, n in l.comb_starts.values():
                if self.offset_bucket is None:
                    out.append(CBlock("%s = _np_pc_%s" % (s.name, s.name)))
                else:
                    out.append(CBlock("%s = _np_pc_%s + %s" % (s.name, s.name,
                                                               " + ".join(["_np_mps_total.el[%d]" % i for i in range(0, self.offset_bucket,)]))))

        return out

    def _executor(self):
        l = self.loop
        
        comb_var = [(s.ty, s.name, " = _np_i") for s in l.comb_sym]

        executor = [CDecl((l.index_type, l.index_var, "")),
                    CondC(l.comb_present, CDecl(comb_var)),
                    CondC(l.closure_present, init_cvars(l.closure_variables, 
                                                      "nps.fg.src[_np_i]")),
                    CBlock(l.index_var + "= nps.fg.itvalue[_np_i]"),
                    l.work.clone() 
                    ]

        return executor                
    
    def executor(self):
        return [CBlock(["", "_np_i = threadIdx.x"]),
                If("_np.valid(_np_i)", self._executor())]

    def sched(self):
        l = self.loop       

        comb_start_update = [Assign(s.name, CBlock(s.name + " + ITSIZE")) for s, n in l.comb_starts.values()] #    "start += ITSIZE"

        return [Uniform(While("_np.work()", 
                              [CDecl(("int", "_np_i", "=0")),
                               CondC(l.closure_present,
                                     CBlock(["_np.inspect2(nps.fg.itvalue, nps.fg.src, ITSIZE, threadIdx.x)",]),
                                     CBlock(["_np.inspect(nps.fg.itvalue, ITSIZE)",])),
                              TB_Barrier().sync()] + 
                              self.executor() + 
                              [CBlock(["_np.execute_round_done(ITSIZE)"])] +
                              CondC(l.comb_present, comb_start_update, []) +
                              [TB_Barrier().sync()]
                              ),
                        place_uniform = True,
                        place_level = TB_Barrier().level,
                        )]

class NPFineGrainedMulti(NPFineGrained1):
    multi_outer = True

    def executor(self):
        return [CBlock(""),
                CFor(["_np_i = threadIdx.x"], 
                     "_np_i < ITSIZE && _np.valid(_np_i)",
                     ["_np_i += BLKSIZE"], self._executor())]

class NPWarp(NPScheduler):
    default_min = "_NP_CROSSOVER_WP"
    multi_outer = False

    def sched(self):
        l = self.loop

        if self.offset_bucket is None:
            comb_start_update = ["nps.warp.offset[warpid] = _np_mps"]
        else:
            comb_start_update = ["nps.warp.offset[warpid] = _np_mps.el[%d]" % (self.offset_bucket,)]

        comb_start_thread_init = ["%s =  _np_pc_%s + nps.warp.offset[warpid]" % (s.name, s.name) for s, n in l.comb_starts.values()]
        comb_var = [(s.ty, s.name, '= _np_ii') for s in l.comb_sym]

        out = []

        out.append(CDecl([("const int", 'warpid', '= threadIdx.x / 32')]))
        out.append(CDecl([("const int", '_np_laneid', '= cub::LaneId()')]))

        sched_filter = get_range_condition(self.range_min, self.range_max)


        x = While("__any(%s)" % (sched_filter,), 
          [If(sched_filter,
              [CBlock("nps.warp.owner[warpid] = _np_laneid")]),

           If("nps.warp.owner[warpid] == _np_laneid",
              [CondC(l.comb_present, CBlock(comb_start_update)),
               CBlock(["nps.warp.start[warpid] = _np.start",
                       "nps.warp.size[warpid] = _np.size",
                       CondC(l.closure_present, 
                             "nps.warp.src[warpid] = threadIdx.x", ""), 
                       "_np.start = 0",
                       "_np.size = 0"]
                      )
               ]
              ),

           CDecl([(l.index_type, "_np_w_start", "= nps.warp.start[warpid]"),
                  (l.index_type, "_np_w_size", "= nps.warp.size[warpid]"),
                  ]),

           CondC(l.closure_present, init_cvars(l.closure_variables, "nps.warp.src[warpid]")),
           CondC(l.comb_present, CBlock(comb_start_thread_init)),

           CFor(CDecl(("int", "_np_ii", "= _np_laneid")), 
                "_np_ii < _np_w_size", 
                "_np_ii += 32",
                [CDecl((l.index_type, l.index_var, "")),
                 CBlock("%s = _np_w_start +_np_ii" % (l.index_var,)),
                 CondC(l.comb_present, CDecl(comb_var)),
                 l.work.clone()]
                ),
           ]
          )

        out.append(x) # x is only uniform at level 2 (warp)
        out.append(TB_Barrier().sync()) # hold back warps ..
        return [Block(out), CBlock("")]

    def post(self):
        if self.nsched > 1:
            return [TB_Barrier().sync()] # protect temp_storage since it is union'ed
        else:
            return []

INVALID_THREAD_ID = "MAX_TB_SIZE + 1" # if index_type is unsigned ...

class NPTB(NPScheduler):
    default_min = "_NP_CROSSOVER_TB"
    multi_outer = False

    def shared_init(self):
        return [CBlock("nps.tb.owner = %s" % (INVALID_THREAD_ID,))]

    def sched(self):
        l = self.loop

        #comb_present = len(comb_sym) > 0
        if self.offset_bucket is None:
            comb_start_update = ["nps.tb.offset = _np_mps"]
        else:
            comb_start_update = ["nps.tb.offset = _np_mps.el[%d]" % (self.offset_bucket,)]

        comb_start_thread_init = ["%s = _np_pc_%s + nps.tb.offset" % (s.name, s.name) for s, n in l.comb_starts.values()]
        comb_var = [(s.ty, s.name, "= _np_j") for s in l.comb_sym]

        out = []

        #out.append(CBlock("BlockScan(nps.temp_storage).ExclusiveSum(_np.size > _NP_CROSSOVER_TB, _np.offset, _np.total)"))

        #out.append(CBlock(["_np.offset = _np_mps.el[1]",
        #                   "_np.total = _np_mps_total.el[1]"]))

        in_split_cond = get_range_condition(self.range_min, self.range_max)

        out.append(Uniform(While("true",
                                 [If(in_split_cond, [CBlock("nps.tb.owner = threadIdx.x")]),
                                  TB_Barrier().sync(),
                                  Uniform(If("nps.tb.owner == %s" % (INVALID_THREAD_ID,), [TB_Barrier().sync(), CBlock("break")])),
                                  If("nps.tb.owner == threadIdx.x",
                                     [CondC(l.comb_present, CBlock(comb_start_update)),
                                      CBlock(["nps.tb.start = _np.start",
                                              "nps.tb.size = _np.size",
                                              "nps.tb.src = threadIdx.x",
                                              "_np.start = 0",
                                              "_np.size = 0",]
                                             )]),

                                  TB_Barrier().sync(),

                                  CDecl([("int", "ns", "= nps.tb.start"),
                                         ("int", "ne", "= nps.tb.size")]),
                                  If("nps.tb.src == threadIdx.x", 
                                     [CBlock("nps.tb.owner = %s" % (INVALID_THREAD_ID,))]),
                                  CondC(l.closure_present, init_cvars(l.closure_variables, "nps.tb.src")),
                                  CondC(l.comb_present, CBlock(comb_start_thread_init)),
                                  
                                  CFor(CDecl(("int", "_np_j", "= threadIdx.x")),
                                       "_np_j < ne","_np_j += BLKSIZE", 
                                       [CDecl((l.index_type, l.index_var, "")),
                                        CBlock(["%s = ns +_np_j" % (l.index_var,)]),
                                        CondC(l.comb_present, CDecl(comb_var)),
                                        self.loop.work.clone()]),

                                  TB_Barrier().sync(),
                                  ]
                                 ),
                           place_uniform = True,
                           place_level = TB_Barrier().level,
                           )
                   )

        out.append(CBlock(""))
        return out

