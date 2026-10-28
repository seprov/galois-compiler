import bmk2
from irglprops import irgl_bmk, PERF_RE

class dmr(irgl_bmk):
	bmk = 'dmr'
	variant = 'irgl'
   
	def filter_inputs(self, inputs):
		return [x for x in inputs if x.props.format == "text/mesh"]

	def get_run_spec(self, bmkinput):
		x = bmk2.RunSpec(self, bmkinput)
		x.set_binary(self.props._cwd, 'dmr')
		bf = bmkinput.props.file[:-4]
		x.set_arg(bf)
		x.set_arg(bmkinput.props.file, bmk2.AT_INPUT_FILE_IMPLICIT)
		x.set_arg(bf + ".node", bmk2.AT_INPUT_FILE_IMPLICIT)
		x.set_arg(bf + ".poly", bmk2.AT_INPUT_FILE_IMPLICIT)
		x.set_arg(bmkinput.props.factor)
		x.set_arg("--no")

		x.set_checker(bmk2.REChecker('^0 \(0\) final bad triangles$'))
		x.set_perf(bmk2.PerfRE('^time: (?P<time_ns>.*) ns$'))
		return x

BINARIES = [dmr()]
