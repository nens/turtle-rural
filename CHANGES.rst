Changelog of turtle-rural
=========================


0.2 (2011-06-09)
----------------

- Fixed ticket 2766: the Makefile to create the Windows installers
  does not function when setuptools is installed as a site package.
- Fixed ticket 2854: the installer stops because it appears to
  incorrectly detect that libraries nens and turtlebase are installed
  as a site package.
- The Windows installer now checks whether the Python libraries nens
  and turtlebase are installed globally. If at least one of them is
  installed globally, the user has to deinstall these libraries.


0.1 (2011-03-30)
----------------

- Copied over existing turtle rural code into the new buildout/setuptools
  based properly packaged version.

- Initial library skeleton created with nensskel.

- Pinnen nens to 1.1, turtlebase to 11.0.
