#

check_SCRIPTS = gmb-test

check_DATA = gmb-test-modules.stamp-h

TESTS = gmb-test

.PHONY: check-prepare

check-prepare: $(check_SCRIPTS) $(check_DATA)

gmb-test-modules.stamp-h: $(GMB_TEST_MODULES_PY)
	echo "TEST MODULES: $(GMB_TEST_MODULES)"
	for mod in $(GMB_TEST_MODULES); do \
		test -e "$$mod.py" || $(LN_S) -v "$(srcdir)/$$mod.py" "$$mod.py"; \
	done
	echo >$@
