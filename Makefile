all: rt bmks 
#ubmks

.PHONY: rt bmks ubmks clean clean-rt clean-ubmks

gensrc:
	mkdir -p gensrc
	make -C bmks/ init-gensrc

rt: 
	make -C rt/src

bmks: gensrc
	make -C bmks

ubmks: 
	make -C ubmks

clean:	 clean-rt clean-ubmks

clean-rt:
	make -C rt/src clean

clean-ubmks:
	make -C ubmks clean

#distclean:
