include ../common.mk
DSTDIR=$(GENSRC)/pr-tp

all: $(DSTDIR) pr-tp

pr-tp: $(DSTDIR)/kernel.cu $(DSTDIR)/support.cu $(DSTDIR)/Makefile  $(DSTDIR)/bmktest2.py $(DSTDIR)/kernel-nontex.cu

$(DSTDIR)/Makefile: 
	ln -sf ../../skelapp/SAMakefile $@

$(DSTDIR)/kernel.cu: pr_tp.py 
	$(GGC) $(GGCFLAGS) -o $@ $<

$(DSTDIR)/support.cu: 
	ln -sf ../../bmks/pr-tp/pr_support.cu $@ 

$(DSTDIR)/kernel-nontex.cu: pr_tp.py 
	$(GGC) $(GGCFLAGS) --cuda-worklist basic --cuda-graph basic -o $@ $<

include ../common-rules.mk

$(DSTDIR)/bmktest2.py: 
	ln -sf ../../bmks/pr-tp/bmktest2.py $@ 
