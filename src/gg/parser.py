#!/usr/bin/env python3
"""Load an IrGL AST, resolving nested Import calls beside the importing file."""
from contextvars import ContextVar
from pathlib import Path
import sys

_source_directory = ContextVar('irgl_source_directory', default=None)


def parse(filename):
    path = Path(filename)
    parent = _source_directory.get()
    if not path.is_absolute() and parent is not None:
        path = parent / path
    path = path.resolve()
    token = _source_directory.set(path.parent)
    namespace = {'__file__': str(path)}
    try:
        exec(compile(path.read_bytes(), str(path), 'exec'), namespace)
    finally:
        _source_directory.reset(token)
    return namespace['ast']


Import = parse

if __name__ == '__main__':
    print(parse(sys.argv[1]))
