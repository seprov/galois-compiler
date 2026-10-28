warp: warp.cu
	nvcc -arch sm_35 $< -o $@

warp.cubin: warp.cu
	nvcc -cubin -arch sm_35 $< -o $@
