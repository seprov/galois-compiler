include ../common.mk

DSTDIR=$(GENSRC)/bfs-tp

all: $(DSTDIR) bfs-tp

bfs-tp: $(DSTDIR)/Makefile $(DSTDIR)/kernel.cu $(DSTDIR)/support.cu $(DSTDIR)/bmktest2.py $(DSTDIR)/kernel-nontex.cu


$(DSTDIR)/Makefile: 
	ln -sf ../../skelapp/SAMakefile $@

$(DSTDIR)/kernel.cu: bfs_tp.py 
	$(GGC) $(GGCFLAGS) -o $@ $<

$(DSTDIR)/support.cu: 
	ln -sf ../../bmks/bfs-topo/bfs_support.cu $@ 

$(DSTDIR)/kernel-nontex.cu: bfs_tp.py 
	$(GGC) $(GGCFLAGS) --cuda-worklist basic --cuda-graph basic -o $@ $<

include ../common-rules.mk

$(DSTDIR)/bmktest2.py: 
	ln -sf ../../bmks/bfs-tp/bmktest2.py $@ 
