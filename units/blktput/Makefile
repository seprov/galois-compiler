all: blktput

blktput: blktput.cu
	nvcc -arch sm_35 -I ../../rt/include -L ../../rt/lib $< -o $@ -lggrt
