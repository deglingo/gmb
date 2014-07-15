#

PYCC = $(abs_top_builddir)/pycc

all-local: gmb-modules.stamp-h

gmb-modules.stamp-h: $(GMB_MODULES_PY) $(PYCC)
	for mod in $(GMB_MODULES); do \
		test -e "$$mod.py" || $(LN_S) -v "$(srcdir)/$$mod.py" "$$mod.py"; \
		$(PYCC) "$$mod.py"; \
	done
	echo >$@

install-exec-hook:
	echo "installing gmb modules"
	test -d "$(pkgpythondir)" || mkdir -vp "$(pkgpythondir)"
	for mod in $(GMB_MODULES); do \
		( cd "$(pkgpythondir)"; test -e "$$mod.py" || $(LN_S) -v "$(abs_top_srcdir)/gmb/$$mod.py" "$$mod.py"; ); \
		( cd "$(pkgpythondir)"; $(PYCC) "$(pkgpythondir)/$$mod.py"; ); \
	done

