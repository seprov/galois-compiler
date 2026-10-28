include ../common.mk
DSTDIR=$(GENSRC)/triangles

all: $(DSTDIR) triangles 

triangles: $(DSTDIR)/Makefile  $(DSTDIR)/kernel.cu $(DSTDIR)/support.cu $(DSTDIR)/bmktest2.py $(DSTDIR)/kernel-nontex.cu

$(DSTDIR)/Makefile: 
	ln -sf ../../skelapp/SAMakefile $@

$(DSTDIR)/kernel.cu: triangles.py 
	$(GGC) $(GGCFLAGS) -o $@ $<

$(DSTDIR)/kernel-nontex.cu: triangles.py 
	$(GGC) $(GGCFLAGS) --cuda-worklist basic --cuda-graph basic -o $@ $<

$(DSTDIR)/support.cu: 
	ln -sf ../../bmks/triangles/tri_support.cu $@ 


include ../common-rules.mk

$(DSTDIR)/bmktest2.py: 
	ln -sf ../../bmks/triangles/bmktest2.py $@ 
