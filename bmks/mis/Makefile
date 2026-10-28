include ../common.mk
DSTDIR=$(GENSRC)/mis

all: $(DSTDIR) mis

mis: $(DSTDIR)/Makefile  $(DSTDIR)/kernel.cu $(DSTDIR)/support.cu $(DSTDIR)/bmktest2.py $(DSTDIR)/kernel-nontex.cu

$(DSTDIR)/Makefile: 
	ln -sf ../../skelapp/SAMakefile $@

$(DSTDIR)/kernel.cu: mis.py 
	$(GGC) $(GGCFLAGS) -o $@ $<

$(DSTDIR)/support.cu: 
	ln -sf ../../bmks/mis/mis_support.cu $@ 

$(DSTDIR)/kernel-nontex.cu: mis.py 
	$(GGC) $(GGCFLAGS) --cuda-worklist basic --cuda-graph basic -o $@ $<

include ../common-rules.mk

$(DSTDIR)/bmktest2.py: 
	ln -sf ../../bmks/mis/bmktest2.py $@ 
