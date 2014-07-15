AC_INIT([gmb], [0.0.0])
AM_INIT_AUTOMAKE

AC_PROG_LN_S

# check for python3
# [FIXME] it looks like AM_PATH_PYTHON is not working with py3 - did I
# miss something ?
AC_SUBST([PYTHON])
AC_SUBST([PYTHON_VERSION])
AC_SUBST([PYTHON_VERSION_MAJ])
AC_SUBST([PYTHON_VERSION_MIN])
AC_MSG_CHECKING([for python3])
if PYTHON="`which python3`"; then
	AC_MSG_RESULT([$PYTHON])
else
	AC_MSG_RESULT([no])
	AC_ERROR([python3 not found])
fi
AC_MSG_CHECKING([for python version])
if ! PYTHON_VERSION_MAJ="`$PYTHON -c 'import sys; print(sys.version_info[[0]])'`"; then
	AC_MSG_RESULT([no])
	AC_ERROR([could not get major python version])
fi
if ! PYTHON_VERSION_MIN="`$PYTHON -c 'import sys; print(sys.version_info[[1]])'`"; then
	AC_MSG_RESULT([no])
	AC_ERROR([could not get minor python version])
fi
PYTHON_VERSION="${PYTHON_VERSION_MAJ}.${PYTHON_VERSION_MIN}"
AC_MSG_RESULT([$PYTHON_VERSION])

# python directories
AC_SUBST([pythondir], '${libdir}/python${PYTHON_VERSION}/site-packages')
AC_SUBST([pkgpythondir], '${pythondir}/${PACKAGE}')

# [FIXME] find nose
AC_SUBST([NOSE2])
NOSE2="`which nose2-3`"

m4_define([gmb_modules], [ \
  __init__ \
  gmbapp \
])

m4_define([gmb_test_modules], [ \
  __init__ \
  test_base \
])

AC_SUBST([GMB_MODULES],    "m4_map_args_w(gmb_modules, [], [],    [ ])")
AC_SUBST([GMB_MODULES_PY], "m4_map_args_w(gmb_modules, [], [.py], [ ])")

AC_SUBST([GMB_TEST_MODULES],     "m4_map_args_w(gmb_test_modules, [], [],     [ ])")
AC_SUBST([GMB_TEST_MODULES_PY],  "m4_map_args_w(gmb_test_modules, [], [.py],  [ ])")

AC_CONFIG_FILES([ \
  Makefile \
  bin/Makefile \
  gmb/Makefile \
  test/Makefile \
])
AC_CONFIG_FILES([pycc], [chmod +x pycc])
AC_CONFIG_FILES([bin/gmb], [chmod +x bin/gmb])
AC_CONFIG_FILES([test/gmb-test], [chmod +x test/gmb-test])
AC_OUTPUT
