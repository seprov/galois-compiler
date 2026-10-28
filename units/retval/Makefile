all: retval

retval: retval.cu
	nvcc -arch sm_35 -I ../../rt/include $< -o $@

retval.cubin: retval.cu
	nvcc -cubin -arch sm_35 -I ../../rt/include $< -o $@
