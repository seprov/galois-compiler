include ../common.mk
DSTDIR=$(GENSRC)/pr-residual-wl

all: $(DSTDIR) pr-residual-wl

pr-residual-wl: $(DSTDIR)/Makefile  $(DSTDIR)/kernel.cu $(DSTDIR)/support.cu $(DSTDIR)/bmktest2.py $(DSTDIR)/kernel-nontex.cu

$(DSTDIR)/Makefile: 
	ln -sf ../../skelapp/SAMakefile $@

$(DSTDIR)/kernel.cu: pr_residual_wl.py 
	$(GGC) $(GGCFLAGS) -o $@ $<

$(DSTDIR)/support.cu: 
	ln -sf ../../bmks/pr-residual-wl/pr_support.cu $@ 

$(DSTDIR)/kernel-nontex.cu: pr_residual_wl.py 
	$(GGC) $(GGCFLAGS) --cuda-worklist basic --cuda-graph basic -o $@ $<

include ../common-rules.mk

$(DSTDIR)/bmktest2.py: 
	ln -sf ../../bmks/pr-residual-wl/bmktest2.py $@ 
