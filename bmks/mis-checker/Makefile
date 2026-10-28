include ../common.mk
DSTDIR=$(GENSRC)/mis-checker

all: $(DSTDIR) mis-checker

mis-checker: $(DSTDIR)/Makefile  $(DSTDIR)/kernel.cu $(DSTDIR)/support.cu $(DSTDIR)/bmktest2.py $(DSTDIR)/kernel-nontex.cu

$(DSTDIR)/Makefile: 
	ln -sf ../../skelapp/SAMakefile $@

$(DSTDIR)/kernel.cu: mis_checker.py 
	$(GGC) $(GGCFLAGS) -o $@ $<

$(DSTDIR)/support.cu: 
	ln -sf ../../bmks/mis-checker/mis_support.cu $@ 

$(DSTDIR)/kernel-nontex.cu: mis_checker.py 
	$(GGC) $(GGCFLAGS) --cuda-worklist basic --cuda-graph basic -o $@ $<

include ../common-rules.mk

$(DSTDIR)/bmktest2.py: 
	ln -sf ../../bmks/mis-checker/bmktest2.py $@ 
