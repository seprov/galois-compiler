from gg.ast import *

ast = Module([
        Kernel("xyz", [],
               [
                CDecl(("int", "x", "")),
                Assign("xy", CExpr("y")),  # this currently works because of some issues with how lhs is parsed
                Assign("x", MethodInvocation("y", "push", "Worklist", ["x"])),
                ])
        ])
