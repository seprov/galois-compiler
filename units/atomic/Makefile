GGC=../../src/ggc

all: atomic

atomic: atomic.cu
	nvcc -arch sm_35 -I ../../rt/include -I ../../rt/include/mgpu/include  -I ../../rt/include/cub $< -o $@

atomic.cubin: atomic.cu
	nvcc -cubin -arch sm_35 -I ../../rt/include -I ../../rt/include/mgpu/include  -I ../../rt/include/cub $< -o $@

atomic.cu: atomic.py
	 $(GGC) $< -o $@
