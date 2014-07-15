#

# keep '.' first for pycc
SUBDIRS = . bin gmb test

all-local: pycc

.PHONY: check-prepare

check-prepare:
	cd test && $(MAKE) $(AM_MAKEFLAGS) check-prepare
