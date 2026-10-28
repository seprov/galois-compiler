include ./common.mk

APPS=bfs-topo bfs-cx bfs-tp bfs-hybrid sssp-topo bfs-wl sssp-wl sssp-nf sssp-wl-noprio mis mst-wl mst-wl-test dmr pr-tp pr-residual pr-residual-wl cc triangles mis-checker mis-pannotia
TARGETDIR=../gensrc
TARGETS=$(addprefix $(TARGETDIR)/, $(APPS))

.PHONY: $(APPS) list-apps

all: $(APPS)

list-apps:
	@echo $(APPS)

init-gensrc: $(TARGETS)

$(TARGETS): 
	mkdir $@

$(APPS): 
	make -C $@
