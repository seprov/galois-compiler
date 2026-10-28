import gg.parser
import gg.unit
import gg.backend.cuda
import logging
import gg.passes
import gg.passes.iteroutliner
import gg.passes.lightener
import gg.passes.props
import gg.passes.uniformizer
import gg.passes.np
import gg.passes.coopconv
import gg.passes.syncheck
import gg.passes.stbuilder
import gg.passes.semcheck
import gg.passes.counter
import gg.passes.parcomb
import gg.passes.desugar
import gg.passes.unroller
import gg.passes.rfpf
import gg.passes.clbuilder
import gg.passes.instr
import gg.passes.omchar
import os

UNROLL_CHOICES = set(['pipes'])
INSTRUMENT_CHOICES = set(['wlatomics', 'wlcontents', 'kstate', 'strip_push', 'omchar', 'wlsort', 'savefilter', 'wlatomicdensity'])
NP_SCHED_CHOICES = set(['tb', 'wp', 'fg'])
HACKS = set(['allow_np_writes', 'lighten-wl'])
INSTRUMENT_MODE = set(['save', 'load'])
LOGLEVEL = set(['INFO', 'DEBUG', 'CRITICAL'])

def get_config():
    backends = {'cuda': gg.backend.cuda}

    return {'backends': backends}

class CompilerOptions(object):
    # some of these are translation unit specific,
    # whereas some apply to the compiler ...

    read_props = None
    write_props = None
    backend = None

    np = False
    np_factor = 1
    np_schedulers = None

    outline_iterate = False
    outline_iterate_gb = False

    coop_conv = False
    parcomb = False
    cc_disable = None

    quiet_cgen = True
    ignore_nested_errors = False

    unroll = None

    logfile = None

    retry_backoff = False
    backoff_blocking_factor = None

    instrument = None
    instrument_mode = None
    hacks = None

    loglevel = 'INFO'
    logfile_level = 'DEBUG'
    

    def __init__(self, backend = "cuda"):
        config = get_config()
        assert backend in config['backends'], backend
        
        self.backend = config['backends'][backend].CompilerOptions()
        self.backend.parent = self
        self.unroll = set()
        self.cc_disable = set()
        self.instrument = set()
        self.hacks = set()

    def __str__(self):
        out = []
        for p, v in vars(self).iteritems():
            if p == "backend":
                out.append(str(self.backend))
            else:
                out.append("%s=%s" % (p, v))

        return " $ ".join(out)


    def by_name(self, name):
        return getattr(self, name)

    def from_dict(self, d):
        # TODO: check dictionary to see if any keys are not recognized

        self.np = d.get('np', False)
        self.np_factor = d.get('np_factor', 1)
        self.np_schedulers = set(d.get('np_schedulers', NP_SCHED_CHOICES))

        self.parcomb = d.get('parcomb', False)
        self.cc_disable = set(d.get('cc_disable', []))

        self.outline_iterate = d.get('outline_iterate', False)
        self.outline_iterate_gb = d.get('outline_iterate_gb', False)

        self.unroll = d.get('unroll', [])

        self.retry_backoff = d.get('backoff', False)
        self.backoff_blocking_factor = d.get('backoff_blocking_factor', [])

        self.instrument = d.get('instrument', [])
        self.instrument_mode = d.get('instrument_mode', None)
       
        
class Compiler(object):
    """Compilation Unit"""
    
    errors = 0

    def __init__(self):
        self.log = logging.getLogger('ggc')
        logging.basicConfig(level=logging.DEBUG)
        self.pm = gg.passes.PassManager()
        
    def info(self, message):
        self.log.info(message)

    def _check(self, cond, message, logger, context = None, _warn = False):
        if not cond:
            if not context:
                context = "module"

            logger("%s: %s" % (context, message))
            
            if not _warn: # use only during development
                self.errors += 1

        return cond

    def check(self, cond, message, context = None):
        return self._check(cond, message, self.log.error, context)

    def check_internal(self, cond, message, context = None, _warn = False):
        return self._check(cond, message, self.log.critical, context, _warn)

    def show_cgen(self, gen):
        return (gen == 0) or not (gen > 0 and self.options.quiet_cgen)

    def check_options(self, options):
        for x in options.unroll:
            assert x in UNROLL_CHOICES, "%s is not a valid unroll choice" % (x,)

        for x in options.instrument:
            assert x in INSTRUMENT_CHOICES, "%s is not a valid instrumentation choice" % (x,)

        for x in options.np_schedulers:
            assert x in NP_SCHED_CHOICES, "%s is not a valid NP scheduler choice" % (x,)

        assert options.loglevel in LOGLEVEL, "%s is not a valid loglevel value" % (x,)
        assert options.logfile_level in LOGLEVEL, "%s is not a valid logfile level value" % (x,)

        return True

    def compile(self, inp, output, options, passes = None):
        self.check_options(options)

        if options.loglevel:
            for h in logging.getLogger('').handlers:
                if isinstance(h, logging.StreamHandler):
                    h.setLevel(logging.getLevelName(options.loglevel))
                    break

        if options.logfile:
            logfile = logging.FileHandler(options.logfile, 'wb')
            fmt = logging.Formatter('%(levelname)-8s %(message)s')
            logfile.setFormatter(fmt)
            logfile.setLevel(logging.getLevelName(options.logfile_level))
            logging.getLogger('').addHandler(logfile)

        if not isinstance(inp, gg.ast.Node):
            ast = gg.parser.parse(inp)
        else:
            ast = inp

        self.unit = gg.unit.TUnit(self, ast)
        
        if options.read_props:
            self.pm.add_pass(gg.passes.props.PropReaderPass(options.read_props))

        self.pm.add_pass(gg.passes.syncheck.SyntaxCheckerPass())
        self.pm.add_pass(gg.passes.stbuilder.SymbolTableBuilderPass())
        self.pm.add_pass(gg.passes.stbuilder.SymbolTableCheckerPass())
        self.pm.add_pass(gg.passes.semcheck.SemanticCheckerPass())
        self.pm.add_pass(gg.passes.desugar.DesugaringPass())
        self.pm.add_pass(gg.passes.clbuilder.ClosureBuilderPass())

        if output:
            self.backend = options.backend
            self.pm.add_pass(self.backend.get_passes(output))
        
        if options.write_props:
            self.pm.add_pass(gg.passes.props.PropWriterPass(options.write_props))

        if 'savefilter' in options.instrument:
            assert options.instrument_mode == 'load', "Cannot save filtering data in non-load modes"
            self.pm.add_pass(gg.passes.instr.SaveFilterPass())

        if 'kstate' in options.instrument or 'wlcontents' in options.instrument:
            assert options.instrument_mode is not None, "instrument_mode can't be empty for kstate or wlcontents"

        if 'kstate' in options.instrument or 'wlcontents' in options.instrument:
            self.pm.add_pass(gg.passes.instr.StateSaverPass())

        if 'strip_push' in options.instrument:
            self.pm.add_pass(gg.passes.instr.WLPushRemoverPass())

        if 'omchar' in options.instrument:
            o = os.path.join(os.path.dirname(output), "omchar.csv")

            assert not isinstance(inp, gg.ast.Node) # not yet supported

            self.pm.add_pass(gg.passes.omchar.OmAnnotatorPass(o, os.path.basename(inp))) # TODO: add path for storing output

        self.pm.add_pass(gg.passes.uniformizer.UniformizerPass())
        self.pm.add_pass(gg.passes.uniformizer.UniformityCheckerPass())

        if options.outline_iterate:
            self.pm.add_pass(gg.passes.iteroutliner.IPOutlinerPass())
            if options.outline_iterate_gb:
                self.pm.add_pass(gg.passes.iteroutliner.IPOutlinerGBPass())
                if 'lighten-wl' in options.hacks:
                    self.pm.add_pass(gg.passes.lightener.LightenKernelsPass())

        if options.coop_conv:
            self.pm.add_pass(gg.passes.coopconv.CoopXformPass())
        else:
            self.pm.add_pass(gg.passes.coopconv.CoopXformStripPass())

        if options.np:
            p = gg.passes.np.NestedParallelismPass()
            self.pm.add_pass(p)
            if options.coop_conv:
                p.depends = list(p.depends) + [('CoopXformPass')]

        self.pm.add_pass(gg.passes.counter.CounterPass())
        self.pm.add_pass(gg.passes.rfpf.RFPFScanPass())

        if options.parcomb:
            p = gg.passes.parcomb.ParCombXformPass()
            self.pm.add_pass(p)
            self.pm.add_pass(gg.passes.parcomb.CoopConvTBPass())
        

        if len(options.unroll):
            p = gg.passes.unroller.UnrollerPass()
            self.pm.add_pass(p)
            
        if passes:
            self.pm.add_pass(passes)

        self.options = options

        return self.pm.run_passes(self)
            
