import bmk2
from irglprops import irgl_bmk, PERF_RE

class mis_checker(irgl_bmk):
	bmk = 'mis-checker'
	variant = 'mis-checker'

	def filter_inputs(self, inputs):
		return [x for x in inputs if x.props.format == 'bin/galois' and 'symmetric' in x.props.flags]

	def get_run_spec(self, bmkinput):
		x = bmk2.RunSpec(self, bmkinput)
		x.set_binary(self.props._cwd, 'test')
		x.set_arg(bmkinput.props.file, bmk2.AT_INPUT_FILE)
		x.set_checker(bmk2.REChecker('^independent: yes, maximal: yes$'))
		x.set_perf(bmk2.PerfRE(PERF_RE))
		return x

#mis-checker sample.sym,sample.sym,sample.sym
BINARIES = [mis_checker()]
