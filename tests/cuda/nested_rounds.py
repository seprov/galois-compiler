"""Uneven, zero-length and partial-block nested work for the CUDA smoke test."""
from gg.ast import Module, Kernel, ForAll, CDecl, CBlock, If, Closure
from gg.ast import While
from gg.ast.anno import Uniform
from gg.types import RangeIterator
from gg.closure import SimpleClosure
capture = SimpleClosure()
capture.add('owner', 'int', 'owner')
capture.add('round', 'int', 'round')
ast = Module([Kernel('nested_copy', [('const int*','sizes'),('int*','values'),
    ('unsigned*','lanes'),('int','count')], [
    ForAll('owner', RangeIterator('count'), [
        CDecl(('bool','pop','= owner < count')),
        CDecl(('int', 'round', '= 0')),
        Uniform(While('round < 3', [
        Closure(ForAll('item',RangeIterator('pop ? sizes[owner] : 0'), [
            CBlock('values[owner * 257 + item] = owner * 1000 + item + round * 10000'),
            CBlock('atomicOr(&lanes[owner], 1u << (threadIdx.x % 32))')]),capture,capture),
        CBlock('++round'),
        ]))
    ])
])])
