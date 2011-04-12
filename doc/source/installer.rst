Installer
=========

.. _NSIS: http://nsis.sourceforge.net/Main_Page

Turtle Rural can be installed using an ordinary Windows setup. In this document
we describe how to create the setup.

To create the setup, we make use the open source system NSIS_ (Nullsoft
Scriptable Install System). You can dowload NSIS `here`__.

__ http://nsis.sourceforge.net/Download

NSIS contains a compiler to create the setup from a text-based configuration
script. The scripting language allows some degree of programmability but not to
the degree we would like. For example, it is not possible to use the same NSIS
script to build installers for Python 2.5 and Python 2.6. We have to modify the
script and then call the compiler on the modified script. To automate this and
prepare other requisites we use a Makefile. The Makefile makes it possible to
reduce the creation of the setup to the execution of a single command.

All the files related to the creation of the installer can be found in the
wininst subdirectory of the Turtle-rural code tree. amely "make py25" to
create the installer for Python 2.5 and "name py26" to create the installer for
Python 2.6.

All the files related to the creation of the installer can be found in the
wininst subdirectory of the Turtle-rural code tree. You have to execute the
command to create the setup from this directory:

#. Open a Command Prompt and change the current directory to the wininst
   subdirectory of the Turtle-rural code tree.
#. To create the installer for Python 2.5, turtle-rural-Python2.5.exe, execute
   "make py25". To create the installer for Python 2.5,
   turtle-rural-Python2.6.exe, execute "make py25".

The Command Prompt will show several messages during execution of the
Makefile. If the installer is successfully created, the last messages printed
should look like this::

  EXE header size:               35840 / 35840 bytes
  Install code:                   4492 / 20331 bytes
  Install data:                8566663 / 10569265 bytes
  Uninstall code+data:            1396 / 1894 bytes
  CRC (0x0FEC09A8):                  4 / 4 bytes

  Total size:                  8608395 / 10627334 bytes (81.0%)
  mv turtle-rural-setup.exe turtle-rural-setup-python2.5.exe

The setup can also install the following Python libraries system-wide, viz.
- matplotlib
- numpy
- scipy
- pyodbc

The installers for these libraries are not part of the Turtle setup. The Turtle
setup just assumes that these installers are present in its working directory.
We decided not to create one setup that includes all as this would result in a
very large setup.  Currently the Turtle setup is almost 9 MB large but the
combined size of the external setups is almost 60 Mb.

Installer design
^^^^^^^^^^^^^^^^

The idea behind the installer is to first it install the required files and
then execute buildout. So when you create the setup, you have to make sure that
these files are in place. This is handled by the Makefile, which performs the
following steps[1]:

- clear the contents of the subdirectories "downloads", "eggs" and "bin"
- create a copy of the installer script[2]
- set the correct Python version in the copy of the installer script
- execute bootstrap
- execute buildout, where buildout uses the download cache "downloads"
- execute the NSIS compiler on the copy of the installer script

The installer scripts collects the required files, among others the contents of
"downloads". The installer itself extracts all the files in the same directory
structure as where they were originally located. This makes the installation
directory a (partial) copy of the directory structure in Subversion. Just as a
developer executes buildout to complete its checkout, the installer runs
buildout to complete the installation.

The installer runs buildout using the "downloads" subdirectory as a download
cache. As this directory contains all the required downloads, buildout does not
require internet access. This is what makes an offline installation of
turtle-rural possible.

.. [1] The directories mentioned in the following steps are all relative to
       root directory of the Turtle-rural code tree.
.. [2] The Makefile and NSIS compiler work on this copy of the installer
       script. The original script is left untouched.
