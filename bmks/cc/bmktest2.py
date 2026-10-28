import bmk2
from irglprops import irgl_bmk, PERF_RE, PERF_DISCOUNTED_RE

class cc(irgl_bmk):
	bmk = 'cc'
	variant = 'irgl'

	def filter_inputs(self, inputs):
		return [x for x in inputs if x.props.format == 'bin/galois' and 'symmetric' in x.props.flags]

	def get_run_spec(self, bmkinput):
		x = bmk2.RunSpec(self, bmkinput)
		x.set_binary(self.props._cwd, 'test')
		x.set_arg(bmkinput.props.file, bmk2.AT_INPUT_FILE)
		x.set_checker(bmk2.REChecker('^components: %s$' % (bmkinput.props.components)))
		x.set_perf(bmk2.PerfRE(PERF_DISCOUNTED_RE))
		return x

#cc rmat12.sym,USA-road-d.USA.sym,rmat20.sym,USA-road-d.NY.sym,2d-2e20.sym,USA-road-d.CAL.sym,USA-road-d.FLA.sym
BINARIES = [cc()]
