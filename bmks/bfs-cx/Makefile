include ../common.mk

DSTDIR=$(GENSRC)/bfs-cx

all: $(DSTDIR) bfs-cx

bfs-cx: $(DSTDIR)/Makefile $(DSTDIR)/kernel.cu $(DSTDIR)/kernel-nontex.cu $(DSTDIR)/support.cu $(DSTDIR)/bmktest2.py

$(DSTDIR)/Makefile: 
	ln -sf ../../skelapp/SAMakefile $@

$(DSTDIR)/kernel.cu: bfs_cx.py 
	$(GGC) $(GGCFLAGS) -o $@ $<

$(DSTDIR)/kernel-nontex.cu: bfs_cx.py 
	$(GGC) $(GGCFLAGS) --cuda-worklist basic --cuda-graph basic -o $@ $<

$(DSTDIR)/support.cu: 
	ln -sf ../../bmks/bfs-topo/bfs_support.cu $@ 


include ../common-rules.mk

$(DSTDIR)/bmktest2.py: 
	ln -sf ../../bmks/bfs-cx/bmktest2.py $@ 
