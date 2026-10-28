all: atomic-nvidia

atomic-nvidia: atomic-nvidia.cu	
	nvcc -arch sm_35 -o $@ $<
