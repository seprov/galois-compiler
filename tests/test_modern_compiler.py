"""Compiler regressions: actual pass execution and deterministic CUDA output."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class CompilerTest(unittest.TestCase):
    def compile(self, source, *options):
        with tempfile.TemporaryDirectory() as work:
            output = Path(work) / 'kernel.cu'
            run = subprocess.run([sys.executable, str(ROOT/'src/ggc'),str(source),
                '-o',str(output),*options], cwd=work, capture_output=True, text=True,
                env=dict(os.environ, PYTHONHASHSEED='0'))
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            if '--logdst' in options:
                self.assertTrue((Path(work)/'ggc.log').read_text())
            return output.read_text(),run.stdout+run.stderr

    def test_help(self):
        subprocess.run([sys.executable, str(ROOT/'src/ggc'),'--help'],check=True,capture_output=True)

    def test_nested_parallelism(self):
        args = ('--opt','np','--nps','fg','--npf','4','--dis-opt','oiter')
        code,log = self.compile(ROOT/'tests/cuda/nested_copy.py',*args)
        self.assertIn('Applying Nested Parallelism',log)
        self.assertNotIn('not applying',log)
        self.assertIn('_np.inspect2',code)
        self.assertIn('__syncthreads()',code)
        repeated,_ = self.compile(ROOT/'tests/cuda/nested_copy.py',*args)
        self.assertEqual(code,repeated)

    def test_uniform_nested_rounds(self):
        code,log = self.compile(ROOT/'tests/cuda/nested_rounds.py',
            '--opt','np','--nps','fg','--npf','4','--dis-opt','oiter')
        self.assertIn('Applying Nested Parallelism',log)
        self.assertIn('while (round < 3)',code)
        self.assertIn('_np.inspect2',code)

    def test_nonuniform_nested_rounds_stay_serial(self):
        source = (ROOT/'tests/cuda/nested_rounds.py').read_text()
        source = source.replace("Uniform(While('round < 3'", "While('round < owner % 3'")
        source = source.replace(']))', '])', 1)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'nonuniform.py'
            path.write_text(source)
            code,log = self.compile(path, '--opt','np','--nps','fg','--npf','4','--dis-opt','oiter')
        self.assertNotIn('Applying Nested Parallelism', log)
        self.assertNotIn('_np.inspect2', code)

    def test_text_logfile(self):
        _,log = self.compile(ROOT/'tests/cuda/nested_copy.py','--logdst','--loglevel','DEBUG')
        self.assertNotIn('Logging error',log)

    def test_serial_lowering(self):
        code,_ = self.compile(ROOT/'tests/cuda/nested_copy.py','--dis-opt','all')
        self.assertNotIn('_np.inspect2',code)
        self.assertIn('for (int item',code)

    def test_original_graph_examples(self):
        programs = [p for p in sorted((ROOT/'bmks').rglob('*.py'))
                    if not p.is_symlink() and 'ast = Module' in p.read_text()]
        self.assertEqual(len(programs),20)
        for source in programs:
            with self.subTest(source=str(source.relative_to(ROOT))):
                code,_ = self.compile(source)
                self.assertIn('__global__',code)

if __name__ == '__main__':
    unittest.main()
