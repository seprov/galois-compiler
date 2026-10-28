import bmk2
from irglprops import irgl_bmk, PERF_RE

class triangles(irgl_bmk):
	bmk = 'triangles'
	variant = 'irgl'

	def filter_inputs(self, inputs):
		return [x for x in inputs if x.props.format == 'bin/galois' and "triangle" in x.props.flags]

	def get_run_spec(self, bmkinput):
		x = bmk2.RunSpec(self, bmkinput)
		x.set_binary(self.props._cwd, 'test')
		x.set_arg(bmkinput.props.file, bmk2.AT_INPUT_FILE)
		x.set_checker(bmk2.REChecker('^triangles: %s$' % (bmkinput.props.triangles)))
		x.set_perf(bmk2.PerfRE(PERF_RE))
		return x

class triangles_irgl_converter(irgl_bmk, bmk2.Converter):
    bmk = 'triangles'
    variant = 'irgl+converter'
    format = "bin/galois"

    def filter_inputs(self, inputs):
        candidates = [x for x in inputs if x.props.format == 'bin/custom' and 'triangle' in x.props.flags]
        #return filter(lambda x: x.get_alt_format(self.format) is None, candidates)
        return candidates


#triangles sample.sym,USA-road-d.NY.sym,rmat12.sym,2d-2e20.sym,USA-road-d.USA.sym,USA-road-d.CAL.sym,USA-road-d.FLA.sym,rmat20.sym,rmat10.sym,rmat22.sym
BINARIES = [triangles()]
CONVERTERS = [triangles_irgl_converter()]
