MAKENSIS="D:/Program Files/NSIS/makensis"

all: py25 py26

py24: MAKE_PYTHONVERSION=2.4
py24: MAKE_PYTHONDIR=Python24
py24: clean create-setup

py25: MAKE_PYTHONVERSION=2.5
py25: MAKE_PYTHONDIR=Python25
py25: clean create-setup

py26: MAKE_PYTHONVERSION=2.6
py26: MAKE_PYTHONDIR=Python26
py26: clean create-setup

clean:
	- rm -rf ../downloads/dist/*.*
	- rm -rf ../downloads/*.*
	- rm -rf ../eggs/*.*
	- rm -rf ../bin/*.*

create-setup:
	cp turtle-rural.nsi autogen-turtle-rural.nsi
	# we escape the dollar sign in the following sed regular expressions,
	# see the '$$', otherwise make would try to expand them
	sed -i 's/\(StrCpy $$PYTHONVERSION[ ][ ]*\).*/\1"$(MAKE_PYTHONVERSION)"/' autogen-turtle-rural.nsi
	sed -i 's/\(StrCpy $$PYTHONDIR[ ][ ]*\).*/\1"C:\\$(MAKE_PYTHONDIR)"/' autogen-turtle-rural.nsi
	sed -i 's/\(zc.buildout-[0-9]*[.][0-9]*[.][0-9]*-py\)[0-9]*[.][0-9]*/\1$(MAKE_PYTHONVERSION)/' autogen-turtle-rural.nsi
	# we use a forward slash as a directory separator in the shell commands
	# as the shell used by make does not like the backslash (or double
	# backslash) as one
	cd ..; c:/$(MAKE_PYTHONDIR)/python bootstrap.py
	cd ..; bin/buildout "buildout:download-cache=downloads"
	$(MAKENSIS) autogen-turtle-rural.nsi
	mv turtle-rural-setup.exe turtle-rural-setup-python$(MAKE_PYTHONVERSION).exe

