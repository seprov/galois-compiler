INC=dmr.h devel.h geomprim.h meshfiles.h dmrggc.inc main.inc bmktest2.py

include ../common.mk

DSTDIR=$(GENSRC)/dmr

OUTINC=$(addprefix $(DSTDIR)/,$(INC))

all: $(DSTDIR) dmr

dmr: $(DSTDIR)/dmr.cu $(OUTINC) $(DSTDIR)/Makefile $(DSTDIR)/dmr-nontex.cu

$(DSTDIR)/Makefile: DMRMakefile
	cp -uv $^ $@

$(DSTDIR)/dmr.cu: dmr.py 
	$(GGC) $(GGCFLAGS) -o $@ $<

$(DSTDIR)/dmr-nontex.cu: dmr.py 
	$(GGC) $(GGCFLAGS) --cuda-worklist basic --cuda-graph basic -o $@ $<

$(OUTINC): $(INC)
	cp -uv $^ $(DSTDIR)

include ../common-rules.mk


