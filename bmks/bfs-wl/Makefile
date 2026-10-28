include ../common.mk

DSTDIR=$(GENSRC)/bfs-wl

all: $(DSTDIR) bfs-wl

bfs-wl: $(DSTDIR)/Makefile  $(DSTDIR)/kernel.cu $(DSTDIR)/support.cu $(DSTDIR)/bmktest2.py $(DSTDIR)/kernel-nontex.cu

$(DSTDIR)/Makefile: 
	ln -sf ../../skelapp/SAMakefile $@

$(DSTDIR)/kernel.cu: bfs_wl.py 
	$(GGC) $(GGCFLAGS) -o $@ $<

$(DSTDIR)/support.cu: 
	ln -sf ../../bmks/bfs-topo/bfs_support.cu $@ 

$(DSTDIR)/kernel-nontex.cu: bfs_wl.py 
	$(GGC) $(GGCFLAGS) --cuda-worklist basic --cuda-graph basic -o $@ $<

include ../common-rules.mk

$(DSTDIR)/bmktest2.py: 
	ln -sf ../../bmks/bfs-wl/bmktest2.py $@ 
