include ../common.mk
DSTDIR=$(GENSRC)/pr-residual

all: $(DSTDIR) pr-residual

pr-residual: $(DSTDIR)/Makefile  $(DSTDIR)/kernel.cu $(DSTDIR)/support.cu $(DSTDIR)/bmktest2.py

$(DSTDIR)/Makefile: 
	ln -sf ../../skelapp/SAMakefile $@

$(DSTDIR)/kernel.cu: pr_residual.py 
	$(GGC) $(GGCFLAGS) -o $@ $<

$(DSTDIR)/support.cu: 
	ln -sf ../../bmks/pr-residual/pr_support.cu $@ 

$(DSTDIR)/kernel-nontex.cu: pr_residual.py 
	$(GGC) $(GGCFLAGS) --cuda-worklist basic --cuda-graph basic -o $@ $<

include ../common-rules.mk

$(DSTDIR)/bmktest2.py: 
	ln -sf ../../bmks/pr-residual/bmktest2.py $@ 
