import bmk2
from irglprops import irgl_bmk, PERF_RE

class bfs_tp(irgl_bmk):
	bmk = 'bfs'
	variant = 'tp'

	def filter_inputs(self, inputs):
		return [x for x in inputs if x.props.format == 'bin/galois' and len(x.props.flags) == 0]

	def get_run_spec(self, bmkinput):
		x = bmk2.RunSpec(self, bmkinput)
		x.set_binary(self.props._cwd, 'test')
		x.set_arg(bmkinput.props.file, bmk2.AT_INPUT_FILE)
		x.set_arg('-o')
		x.set_arg('@output', bmk2.AT_TEMPORARY_OUTPUT)
		x.set_checker(bmk2.DiffChecker('@output', bmkinput.props.bfs_output))
		x.set_perf(bmk2.PerfRE(PERF_RE))
		return x

#bfs USA-road-d.USA,r4-2e23,t33-2,rmat22,USA-road-d.NY,USA-road-d.CAL,t33
BINARIES = [bfs_tp()]
