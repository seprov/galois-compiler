include ../common.mk

DSTDIR=$(GENSRC)/cc

all: $(DSTDIR) cc

cc: $(DSTDIR)/Makefile  $(DSTDIR)/kernel.cu $(DSTDIR)/support.cu $(DSTDIR)/bmktest2.py $(DSTDIR)/kernel-nontex.cu

$(DSTDIR)/Makefile: 
	ln -sf ../../skelapp/SAMakefile $@

$(DSTDIR)/kernel.cu: cc.py 
	$(GGC) $(GGCFLAGS) -o $@ $<

$(DSTDIR)/support.cu: 
	ln -sf ../../bmks/cc/cc_support.cu $@ 

$(DSTDIR)/kernel-nontex.cu: cc.py 
	$(GGC) $(GGCFLAGS) -o $@ $< --cuda-worklist basic --cuda-graph basic

include ../common-rules.mk

$(DSTDIR)/bmktest2.py: 
	ln -sf ../../bmks/cc/bmktest2.py $@ 
