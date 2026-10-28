include ../common.mk

DSTDIR=$(GENSRC)/sssp-nf

all: $(DSTDIR) sssp-nf

sssp-nf: $(DSTDIR)/Makefile $(DSTDIR)/kernel.cu $(DSTDIR)/support.cu $(DSTDIR)/bmktest2.py $(DSTDIR)/kernel-nontex.cu

$(DSTDIR)/Makefile: 
	ln -sf ../../skelapp/SAMakefile $@

$(DSTDIR)/kernel.cu: sssp_nf.py 
	$(GGC) $(GGCFLAGS) -o $@ $<

$(DSTDIR)/kernel-nontex.cu: sssp_nf.py 
	$(GGC) $(GGCFLAGS) --cuda-worklist basic --cuda-graph basic -o $@ $<

$(DSTDIR)/support.cu: sssp_support.cu
	cp -uv $< $@

include ../common-rules.mk

$(DSTDIR)/bmktest2.py: bmktest2.py 
	cp -uv $< $@
