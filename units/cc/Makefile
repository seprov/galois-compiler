all: cc

cc.cu: cc.py
	../../src/ggc --dis-opt oiter --opt parcomb $< -o $@

cc: cc.cu
	../../src/ggc_nvcc -arch sm_35 -o $@ $<
