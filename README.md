# Galois IrGL compiler: Python 3 compatibility port

This fork starts from the original [2019 compiler distribution](https://www.cs.rochester.edu/u/sree/ggc/).
It preserves the IrGL AST, compiler passes and CUDA backend. IrGL schedules
explicit parallel loops; it does not automatically parallelize arbitrary C++
helpers or dependent tree mutations.

## Install and test the compiler

Python 3.10 or newer is required. Python 3.13 has been tested locally on macOS
and on the Linux/WSL GPU machine; CI is configured for 3.10 and 3.13.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/ggc --help
.venv/bin/python -m unittest discover -s tests -p 'test_modern*.py' -v
```

The port updates Python syntax/imports and dependency packaging, preserves the
custom `Worklist.items()` iterator, uses text logging, and resolves nested AST
imports relative to their source files. Tests cover all 20 original benchmark
ASTs with default compiler options, deterministic nested-parallel generation,
serial lowering and logging. Nested scheduling also supports explicitly
`Uniform` sequential `While` loops inside the outer `ForAll`, for repeated
cooperative stages. Unannotated loops do not receive this transformation; callers
must ensure all threads in a block take the same loop iterations. Generating their CUDA does **not** certify that
all original applications build or run on current CUDA.

## CUDA 13 nested-parallel execution

The standalone test uses the `irgl_nested.cuh` runtime header in the sibling
[Galois fork](../Galois/libgpu/include/irgl_nested.cuh). It requires no graph
inputs, old CUB submodule, ModernGPU, LLVM, or full Galois build.

```sh
cmake -S tests/cuda -B build-cuda \
  -DCMAKE_CUDA_ARCHITECTURES=86 \
  -DPython3_EXECUTABLE="$PWD/.venv/bin/python" \
  -DGALOIS_SOURCE_DIR="$PWD/../Galois"
cmake --build build-cuda -j2
ctest --test-dir build-cuda --output-on-failure
```

For a locally unpacked CUDA toolkit, also set `CMAKE_CUDA_COMPILER` to its `nvcc`
and include its `lib` directory in `LD_LIBRARY_PATH` when running tests.
The tests cover repeated uniform stage loops as well as empty and uneven inner loops, partial blocks, multiple work
rounds, output bounds, and participation by all 32 lanes for sufficiently long
inner loops. The tested hardware is an RTX 3090 with CUDA 13.2.

`tools/generate_nested.py` runs the real compiler with its fine-grained nested
scheduler. It rejects skipped parallelization, substitutes the standalone
runtime include, selects the block size, and removes graph-application
boilerplate. It preserves the raw CUDA, the exact adaptation diff and source
hashes beside the generated header. It does not implement a replacement scheduler.

## Remaining modernization

The full graph/worklist runtime and original application Makefiles remain
legacy. Next work is modern CUB/CCCL and ModernGPU integration, checking warp
masks and synchronization for independent thread scheduling, testing worklist
capacity and conflict/retry behavior, and GPU CI. CUDA 12 compatibility and other
GPUs are targets, not validated support claims. The current tests exercise the
fine-grained nested scheduler only.

The imported archive references `LICENSE.TXT` but does not contain it. Compiler
licensing provenance still needs confirmation; the separate Galois repository's
license should not be assumed to cover this compiler archive.
