#!/bin/sh

grep -H 'CRITICAL' "$@" > critical.log
grep -H 'ReduceAndReturn' "$@" > rfpf.log
grep -H 'parcomb' "$@" > parcomb.log
grep -H 'Nested Parallelism\|Nested ForAll' "$@" > nested.log
grep -H 'not outlining\|Outlined' "$@" > iteroutliner.log
