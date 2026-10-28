"""Uneven, zero-length and partial-block nested work for the CUDA smoke test."""
from gg.ast import Module, Kernel, ForAll, CDecl, CBlock, If, Closure
from gg.types import RangeIterator
from gg.closure import SimpleClosure
capture = SimpleClosure()
capture.add('owner', 'int', 'owner')
ast = Module([Kernel('nested_copy', [('const int*','sizes'),('int*','values'),
    ('unsigned*','lanes'),('int','count')], [
    ForAll('owner', RangeIterator('count'), [
        CDecl(('bool','pop','= owner < count')),
        Closure(ForAll('item',RangeIterator('pop ? sizes[owner] : 0'), [
            CBlock('values[owner * 257 + item] = owner * 1000 + item'),
            CBlock('atomicOr(&lanes[owner], 1u << (threadIdx.x % 32))')]),capture,capture)
    ])
])])
