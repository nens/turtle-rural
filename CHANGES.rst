Changelog of turtle-rural
=========================


3.4 (unreleased)
----------------

- Nothing changed yet.


3.3 (2012-10-15)
----------------

- Nothing changed yet.


3.2 (2012-07-16)
----------------

- Nothing changed yet.


3.1 (2011-12-12)
----------------

- Miscellaneous updates.
- Update of nens to 1.10 (from 1.6).
- Update of turtlebase to 11.8 (from 11.6).


3.0.2 (2011-08-09)
------------------

- Nothing changed yet.


3.0.1 (2011-08-03)
------------------

- Nothing changed yet.


3.0 (2011-07-18)
----------------

- Nothing changed yet.


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
