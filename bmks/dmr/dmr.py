# -*- mode: python -*-

from gg.ast import *
from gg.lib.mesh import Mesh
from gg.lib.wl import Worklist
from gg.ast.anno import *
from gg.backend.cuda.anno import LaunchBounds
import cgen

WL = Worklist()
M = Mesh("mesh")

ast = Module([
        CBlock([cgen.Define("CAVLEN", 256),
                cgen.Define("BCLEN", 1024),
                cgen.Include("dmrggc.inc", False)]),
        # ForAll(Uniform(Offset(, etc.)))
        Kernel("check_triangles", [('Mesh', 'mesh'), 
                                   ('unsigned int *', 'bad_triangles'),
                                   ('int', 'start')],
               [CDecl([("uint3*", "el", ""), 
                       ("int", "count", "= 0")]),
                ForAll("ele", M.triangles(offset="start"),
                       [If("ele < mesh.nelements", # not needed?
                           [If("!(mesh.isdel[ele] || IS_SEGMENT(mesh.elements[ele]))",
                               [If("!mesh.isbad[ele]", 
                                   [CBlock(["el = &mesh.elements[ele]",
                                            "mesh.isbad[ele] = (angleLT(mesh, el->x, el->y, el->z) || angleLT(mesh, el->z, el->x, el->y) || angleLT(mesh, el->y, el->z, el->x))"])], []),
                                If("mesh.isbad[ele]", 
                                   [CBlock("count++"),
                                    WL.push("ele")])
                                ])
                            ])
                        ]
                       ),
                CBlock("atomicAdd(bad_triangles, count)")
                ]
               ),
        
        LaunchBounds(Kernel("refine", [('Mesh', 'mesh'),
                                       ('int', 'debg'),
                                       ('uint *', 'nnodes'),
                                       ('uint *', 'nelements')], 
                            [CDecl([("uint", "cavity[CAVLEN]", ""),
                                    ("uint", "nc", "= 0"),
                                    ("uint", "boundary[BCLEN]", ""),
                                    ("uint", "bc", "= 0"),
                                    ("uint", "blnodes[BCLEN/4]", ""),
                                    ("bool", "repush", "= false"),
                                    ("int", "stage", "= 0"),
                                    ("int", "x", "= 0")]),
                             BlockDistribution(ForAll("wlele", WL.items(), [
                                CDecl([("FORD", "cx", ""), ("FORD", "cy", "")]),
                                CBlock(["nc = 0",
                                        "bc = 0",
                                        "repush = false",
                                        "stage = 0"]),
                                CDecl([("bool", "pop", ""), ("int", "ele", "")]),
                                WL.pop("pop", "wlele", "ele"),
                                If("pop && ele < mesh.nelements && "
                                   "mesh.isbad[ele] && !mesh.isdel[ele]", 
                                   [CBlock("cavity[nc++] = ele"),
                                    CDecl(("uint", "oldcav","")),
                                    DoWhile("cavity[0] != oldcav",
                                            [CBlock(["oldcav = cavity[0]",
                                                     "cavity[0] = opposite(mesh, ele)"])]),
                                    If("!build_cavity(mesh, cavity, nc, CAVLEN, boundary, bc, cx, cy)", [CBlock("build_cavity(mesh, cavity, nc, CAVLEN, boundary, bc, cx, cy)")]),                                                               
                                    # CFor(CDecl([("int", "i", "= 0"), 
                                    #             ("int", "k", "=0")]),
                                    #      "i < bc",
                                    #      ["i+=4", "k++"],
                                    #      [CBlock("blnodes[k] = boundary[i+2]")]),
                                    ]),
                                CDecl([("int", "nodes_added", "= 0"),
                                       ("int", "elems_added", "= 0")
                                       ]
                                      ),
                                Exclusive([("mesh", [("nc", "(int *) cavity"), 
                                                     ExclusiveArrayIterator("(int *) boundary", "2", "bc", "4")])],
                                          [If("nc > 0", [CBlock(["nodes_added = 1",
                                                                 "elems_added = (bc >> 2) + (IS_SEGMENT(mesh.elements[cavity[0]]) ? 2 : 0)"]),
                                                         CDecl([("uint", "cnode", ""), 
                                                                ("uint", "cseg1", "= 0"),
                                                                ("uint", "cseg2", "= 0"), 
                                                                ("uint", "nelements_added", ""),
                                                                ("uint", "oldelements", ""),
                                                                ("uint", "newelemndx", "")]),
                                                         CBlock(["cnode = add_node(mesh, cx, cy, atomicAdd(nnodes, 1))",
                                                                 "nelements_added = elems_added",
                                                                 "oldelements = atomicAdd(nelements, nelements_added)",
                                                                 "newelemndx = oldelements"]),
                                                         If("IS_SEGMENT(mesh.elements[cavity[0]])", [CBlock(["cseg1 = add_segment(mesh, mesh.elements[cavity[0]].x, cnode, newelemndx++)","cseg2 = add_segment(mesh, cnode, mesh.elements[cavity[0]].y, newelemndx++)"])]),
                                                         CFor(CDecl(("int", "i", "= 0")), "i < bc", "i+=4", 
                                                              [CDecl(("uint","ntri","= add_triangle(mesh, boundary[i], boundary[i+1], cnode, boundary[i+2], boundary[i+3], newelemndx++)"))]),
                                                         CBlock([
                                                        "assert(oldelements + nelements_added == newelemndx)", 
                                                        "setup_neighbours(mesh, oldelements, newelemndx)", "repush = true"]),
                                                         CFor(CDecl(("int","i","= 0")),
                                                              "i < nc",
                                                              "i++",
                                                              [CBlock(["mesh.isdel[cavity[i]] = true"]),If("cavity[i] == ele", [CBlock("repush = false")])],
                                                              ),
                                                         ]
                                              )
                                           ], # Exclusive
                                          [CBlock("repush = true")]),
                                GlobalBarrier().sync(),
                                If("repush", [Retry("ele", merge=True)]),
                                ])), # forall
                             ], _emit = True),
                     max_threads="TB_SIZE",
                     ),
        Kernel("refine_mesh", [('ShMesh&', 'mesh'),
                               ('dim3', 'blocks'),
                               ('dim3', 'threads')], 
               [CDecl([("Shared<uint>", "nbad", "(1)"),
                       ("Mesh", "gmesh", "(mesh)"),
                       ("Shared<uint>", "nelements", "(1)"), 
                       ("Shared<uint>", "nnodes", "(1)"),
                       ("int", "cnbad", ""),
                       ("bool", "orig", "= false"),
                       ('ggc::Timer', 't', '("total")')]),
                Exclusive.setup("mesh.maxnelements", "refine"),
                GlobalBarrier().setup("refine"),
                CBlock(["find_neighbours_cpu(mesh)",
                        "gmesh.refresh(mesh)",
                        "*(nelements.cpu_wr_ptr(true)) = mesh.nelements", 
                        "*(nnodes.cpu_wr_ptr(true)) = mesh.nnodes",
                        ]),
                Pipe([
                        CDecl(("int", "lastnelements", "= 0")),
                        CBlock(["*(nbad.cpu_wr_ptr(true)) = 0",
                                "t.start()"]),
                        Invoke("check_triangles", ["gmesh", "nbad.gpu_wr_ptr()", "0"]),
                        CBlock('printf("%d initial bad triangles\\n", *(nbad.cpu_rd_ptr()) );'),
                        Pipe([
                                CBlock("lastnelements = gmesh.nelements"),
                                Invoke("refine", ["gmesh", 32, "nnodes.gpu_wr_ptr()", "nelements.gpu_wr_ptr()"],
                                       _noadvance = True),
                                CBlock(["gmesh.nnodes = mesh.nnodes = *(nnodes.cpu_rd_ptr())",
                                        "gmesh.nelements = mesh.nelements = *(nelements.cpu_rd_ptr())",
                                        "*(nbad.cpu_wr_ptr(true)) = 0"]),
                                CBlock("printf(\"checking triangles ...\\n\")"),
                                Invoke("check_triangles", ["gmesh", "nbad.gpu_wr_ptr()", "lastnelements"],
                                       _alt = ('orig', 'check_triangles_orig')),
                                CBlock('printf("%d bad triangles\\n", *(nbad.cpu_rd_ptr()) )'),]),
                        CBlock(["t.stop()",
                                'printf("time: %llu ns\\n", t.duration())']),
                        Pipe([CBlock("*(nbad.cpu_wr_ptr(true)) = 0"),
                              Invoke("check_triangles", ["gmesh", "nbad.gpu_wr_ptr()", "0"]),
                              CBlock('printf("%d (%d) final bad triangles\\n", *(nbad.cpu_rd_ptr()), pipe.in_wl().nitems() )')], once=True),
                        ], WLInit("mesh.nelements"), once=True),
                ], host=True),
        # Kernel("gg_main", [('CSRGraph&', 'hg'), ('CSRGraph&', 'gg')], 
        #        []
        #        ),
        CBlock([cgen.Include('main.inc', system=False)])
        ]) #module
