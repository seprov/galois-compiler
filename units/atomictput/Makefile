all: atomictput

atomictput: atomictput.cu 
	nvcc -g -gencode arch=compute_20,code=sm_20 -gencode arch=compute_35,code=sm_35 -gencode arch=compute_52,code=sm_52 -I../../rt/include $< -o $@

