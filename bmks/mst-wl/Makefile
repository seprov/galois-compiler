include ../common.mk

GC=~/src/GaloisCpp/trunk/default/tools/graph-convert/graph-convert
DSTDIR=$(GENSRC)/mst-wl

all: $(DSTDIR) mst-wl

mst-wl: $(DSTDIR)/Makefile $(DSTDIR)/kernel.cu $(DSTDIR)/support.cu $(DSTDIR)/mst.h $(DSTDIR)/bmktest2.py $(DSTDIR)/kernel-nontex.cu

$(DSTDIR)/Makefile: 
	ln -sf ../../skelapp/SAMakefile $@

$(DSTDIR)/kernel.cu: mst_wl.py 
	$(GGC) $(GGCFLAGS) -o $@ $<

$(DSTDIR)/support.cu: 
	ln -sf ../../bmks/mst-wl/mst_support.cu $@ 

$(DSTDIR)/mst.h: 
	ln -sf ../../bmks/mst-wl/mst.h $@ 

$(DSTDIR)/kernel-nontex.cu: mst_wl.py 
	$(GGC) $(GGCFLAGS) --cuda-worklist basic --cuda-graph basic -o $@ $<

simple.sym.gr: simple.dimacs
	 $(GC) --dimacs2gr simple.dimacs simple.gr && $(GC) --gr2sintgr simple.gr simple.sym.gr

include ../common-rules.mk

$(DSTDIR)/bmktest2.py: 
	ln -sf ../../bmks/mst-wl/bmktest2.py $@ 
