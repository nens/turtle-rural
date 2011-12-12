; example2.nsi
;
; This script is based on example1.nsi, but it remember the directory,
; has uninstall support and (optionally) installs start menu shortcuts.
;
; It will install example2.nsi into a directory that the user selects,
;--------------------------------

Var APPNAME
Var PYTHONVERSION
Var PYTHONDIR

; Set the name of the language
LoadLanguageFile "Dutch.nlf"

AddBrandingImage top 31

; The name of the installer
Name $APPNAME

; Caption of the installer
Caption "Installatie $APPNAME voor Python $PYTHONVERSION"

; The name of the setup file
OutFile "turtle-rural-setup.exe"

; Set default installation directory. Ideally we would like to use the $APPNAME
; variable but InstallDir does not seem to support that.
InstallDir "$PROGRAMFILES\Nelen & Schuurmans\Turtle-rural"

; Registry key to check for directory (so if you install again, it will
; overwrite the old one automatically)
InstallDirRegKey HKLM Software\NSIS_Turtle-rural "Install_Dir"

; Request application privileges for Windows Vista
RequestExecutionLevel admin

ShowInstDetails hide

Function .onInit

  ; Variable APPNAME should not contain spaces as it is also used in the name
  ; of Windows registry keys

  StrCpy $APPNAME       "Turtle-rural"
  StrCpy $PYTHONVERSION "2.5"
  StrCpy $PYTHONDIR     "C:\Python25"

  ; Extract InstallOptions files
  ; $PLUGINSDIR will automatically be removed when the installer closes
  InitPluginsDir
  File "/oname=$PLUGINSDIR\python-location.ini" python-location.ini
  File "/oname=$PLUGINSDIR\conflicting-packages.ini" conflicting-packages.ini
  File "/oname=$PLUGINSDIR\logo.bmp" logo.bmp
  File "/oname=$PLUGINSDIR\check_nens.py" check_nens.py
  File "/oname=$PLUGINSDIR\check_turtlebase.py" check_turtlebase.py

FunctionEnd

Function un.onInit

  ; Variable APPNAME should not contain spaces as it is also used in the name
  ; of Windows registry keys

  StrCpy $APPNAME "Turtle-rural"

FunctionEnd

Function .onGUIInit
  SetBrandingImage "$PLUGINSDIR\logo.bmp"
FunctionEnd

Function un.onGUIInit
  SetBrandingImage "$INSTDIR\logo.bmp"
FunctionEnd

;--------------------------------

; Pages

Page custom PythonLocationPage leavePythonLocationPage
Page custom ConflictingPackagesPage leaveConflictingPackagesPage
Page components
Page directory
Page instfiles

UninstPage uninstConfirm
UninstPage instfiles

Function PythonLocationPage

  ; To test whether Python is installed, we execute "pythonw -h" to
  ; display the command-line options. Initially we used command-line
  ; parameter "--version" but that parameter is not supported by
  ; Python 2.4

  ExecWait "$PYTHONDIR\pythonw.exe -h"
  IfErrors clearPythonLocation setPythonLocation

  clearPythonLocation:
    WriteINIStr "$PLUGINSDIR\python-location.ini" "Field 1" "Text" "We hebben geen geschikte installatie van Python $PYTHONVERSION gevonden. Selecteer hieronder de installatiedirectory."
    WriteINIStr "$PLUGINSDIR\python-location.ini" "Field 2" "State" ""
    Goto show
  setPythonLocation:
    WriteINIStr "$PLUGINSDIR\python-location.ini" "Field 1" "Text" "We hebben een installatie van Python $PYTHONVERSION gevonden in de onderstaande directory. Is dat niet de gewenste installatie, selecteer dan hieronder de juiste directory."
    WriteINIStr "$PLUGINSDIR\python-location.ini" "Field 2" "State" "$PYTHONDIR"

  show:
    InstallOptions::initDialog "$PLUGINSDIR\python-location.ini"
    InstallOptions::show

FunctionEnd

Function leavePythonLocationPage

  ReadINIStr $PYTHONDIR "$PLUGINSDIR\python-location.ini" "Field 2" "State"
  ExecWait "$PYTHONDIR\pythonw.exe -h"
  IfErrors revisitPage
  Return

  revisitPage:
    MessageBox MB_ICONEXCLAMATION|MB_OK	"De opgegeven directory bevat geen Python installatie. Kies een andere directory of annuleer de installatie."
    Abort

FunctionEnd

Function ConflictingPackagesPage

  Var /GLOBAL PACKAGES

  StrCpy $PACKAGES ""

  ExecWait "$PYTHONDIR\pythonw.exe $PLUGINSDIR\check_nens.py"
  IfErrors +1 +2
  StrCpy $PACKAGES "- nens\n"

  ExecWait "$PYTHONDIR\pythonw.exe $PLUGINSDIR\check_turtlebase.py"
  IfErrors +1 +2
  StrCpy $PACKAGES "$PACKAGES- turtlebase\n"

  StrCmp $PACKAGES "" 0 show
  Return

  show:
    WriteINIStr "$PLUGINSDIR\conflicting-packages.ini" "Field 2" "Text" $PACKAGES
    InstallOptions::initDialog "$PLUGINSDIR\conflicting-packages.ini"
    InstallOptions::show

FunctionEnd

Function leaveConflictingPackagesPage

  ExecWait "$PYTHONDIR\pythonw.exe $PLUGINSDIR\check_nens.py"
  IfErrors revisitPage

  ExecWait "$PYTHONDIR\pythonw.exe $PLUGINSDIR\check_turtlebase.py"
  IfErrors revisitPage
  Return

  revisitPage:
    MessageBox MB_ICONEXCLAMATION|MB_OK	"De opgegeven bibliotheken conflicteren met de installatie. Deinstalleer deze bibliotheken of annuleer de installatie."
    Abort

FunctionEnd

;--------------------------------

SectionGroup /e "Externe bibliotheken"

; Optional section (can be disabled by the user)
Section "Matplotlib 1.0.1"

  DetailPrint "Installing Matplotlib..."

  Sleep 1000

  ExecWait "$EXEDIR/matplotlib-1.0.1.win32-py$PYTHONVERSION.exe"

SectionEnd

; Optional section (can be disabled by the user)
Section "Numpy 1.5.1"

  DetailPrint "Installing Numpy..."

  Sleep 1000

  ExecWait "$EXEDIR/numpy-1.5.1-win32-superpack-python$PYTHONVERSION.exe"

SectionEnd

; Optional section (can be disabled by the user)
Section "Scipy 0.9.0"

  DetailPrint "Installing Scipy..."

  Sleep 1000

  ExecWait "$EXEDIR/scipy-0.9.0-win32-superpack-python$PYTHONVERSION.exe"

SectionEnd

; Optional section (can be disabled by the user)
Section "Pyodbc 2.1.7"

  DetailPrint "Installing Pyodbc..."

  Sleep 1000

  ExecWait "$EXEDIR/pyodbc-2.1.7.win32-py$PYTHONVERSION.exe"

SectionEnd

SectionGroupEnd

; The stuff to install
Section "Turtle-rural (required)"

  SectionIn RO

  DetailPrint "Installing Turtle-rural..."

  Sleep 1000

  ; Set output path to the installation directory.
  SetOutPath $INSTDIR

  ; We copy the logo that is used by the installer in the installation
  ; directory so it is also available to the uninstaller
  File "logo.bmp"

  ; Put file there
  File "install.py"
  File "..\buildout.cfg"
  File "..\setup.py"
  File "..\CHANGES.rst"
  File "..\CREDITS.rst"
  File "..\LICENSE.rst"
  File "..\README.rst"
  File "..\TODO.rst"

  SetOutPath $INSTDIR\doc\source

  File "..\doc\source\*.*"

  SetOutPath $INSTDIR\turtle_rural

  File "..\turtle_rural\*.ini"
  File "..\turtle_rural\*.py"
  File "..\turtle_rural\*.tbx"

  ; We install the eggs that bin\buildout requires. Usually, bootstrap
  ; downloads these eggs for us but we cannot assume we have Internet access
  ; during an installation.

  SetOutPath $INSTDIR\eggs
  File "..\eggs\setuptools*.egg"
  ; Unfortunately we have to install the following egg using its precies
  ; directory name. This makes the command rather fragile but NSIS does not
  ; allow wildcards in directories.
  File /r "..\eggs\zc.buildout-1.4.4-py2.5.egg"

  ; We install the eggs that buildout would usually download. Remember, we
  ; cannot assume we have Internet access during installation.

  SetOutPath $INSTDIR\downloads
  File /r "..\downloads\*.*"

  ; The following command replaces the usual bootstrap and bin/buildout
  ; procedure.
  SetOutPath $INSTDIR
  nsExec::ExecToLog '"$PYTHONDIR\python.exe" install.py'

  ; Write the installation path into the registry
  WriteRegStr HKLM SOFTWARE\NSIS_Turtle-rural "Install_Dir" "$INSTDIR"

  ; Write the uninstall keys for Windows
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Turtle-rural" "DisplayName" "Turtle-rural"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Turtle-rural" "Publisher" "Nelen & Schuurmans"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Turtle-rural" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Turtle-rural" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Turtle-rural" "NoRepair" 1
  WriteUninstaller "uninstall.exe"

SectionEnd

;--------------------------------

; Uninstaller

Section "Uninstall"

  ; Remove registry keys
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Turtle-rural"
  DeleteRegKey HKLM Software\NSIS_Turtle-rural

  ; Remove the installed files and the uninstaller
  Delete "$INSTDIR\turtle_rural\*.tbx"
  Delete "$INSTDIR\turtle_rural\*.py"
  Delete "$INSTDIR\turtle_rural\*.ini"
  Delete "$INSTDIR\doc\source\*.*"
  Delete "$INSTDIR\doc\*.*"
  Delete "$INSTDIR\TODO.rst"
  Delete "$INSTDIR\README.rst"
  Delete "$INSTDIR\LICENSE.rst"
  Delete "$INSTDIR\CREDITS.rst"
  Delete "$INSTDIR\CHANGES.rst"
  Delete "$INSTDIR\setup.py"
  Delete "$INSTDIR\buildout.cfg"
  Delete "$INSTDIR\install.py"
  Delete "$INSTDIR\logo.bmp"
  Delete "$INSTDIR\uninstall.exe"

  ; The following directories are only removed when they are completely empty
  RMDir "$INSTDIR\turtle_rural"
  RMDir "$INSTDIR\doc\source"
  RMDir "$INSTDIR\doc"
  RMDir "$INSTDIR"

SectionEnd
