from gg.ast import ASTNodeAnno

class AlternateMethod(ASTNodeAnno):
    method = None
    
    def __init__(self, method):
        self.method = method

class CoopAnno(AlternateMethod):
    coop_only = False

class ParCombAnno(AlternateMethod):
    parcomb_only = False
    combiner_method = None
    combiner_type = None

    def clone(self):
        x = ParCombAnno(self.method.clone())
        x.combiner_method = self.combiner_method.clone() if self.combiner_method else None
        x.combiner_type = self.combiner_type if self.combiner_type else None
        return x

class CoopConvAnno(ASTNodeAnno):
    setup_methods = None
    task_method = None
    at_entry_exit = None
    combiner_type = None

    def __init__(self, task_method, setup_methods, combiner_type):
        self.setup_methods = setup_methods        
        self.task_method = task_method
        self.combiner_type = combiner_type

    def clone(self):
        tm = self.task_method.clone() if self.task_method else None
        sm = self.setup_methods.copy()
        ct = self.combiner_type if self.combiner_type else None

        x = CoopConvAnno(tm, sm, ct)
        return x
        
