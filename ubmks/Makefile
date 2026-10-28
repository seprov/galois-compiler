SRCS = basic-atomic.py  basic-exclusive.py  cblktests.py  coop-bfs-wl.py  simple.py nptest.py
OUT = $(SRCS:.py=.cu)
BIN = $(OUT:.cu=.o)
GGC = ../src/ggc

all: $(OUT)

binaries: $(BIN)

%.cu: %.py
	$(GGC) -o $@ $<

%.o : %.cu
	nvcc -arch sm_35 -O3 -I ../rt/include -I ../rt/include/mgpu/include -lggrt -L ../rt/lib --compile -o $@ $<

%: %.o
	nvcc -arch sm_35 -O3 -o $@ $< -lggrt -L ../rt/lib

cblktests.o: cblktests.cu
	echo "Skipping $@ ..."

clean:
	rm -f $(OUT)
	rm -f $(BIN)
	rm -f $(SRCS:.py=.pyc)
