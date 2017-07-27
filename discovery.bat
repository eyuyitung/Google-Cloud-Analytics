ECHO OFF


rem/////////////////////////// CHANGE TO DESIRED SAMPLE LENGTH ////////////////////////////////
rem/////week is 168 hours, month is 720 hours/////
set HOURS=24



set fpath=%~sdp0

ECHO  - Step 1 - GCP Discovery
python %fpath%src\main.py -t %HOURS%
if errorlevel 1 (GOTO END)

ECHO  - Step 2 - GCP Config
move %fpath%gcp_config.csv %fpath%conf\gcp_config.csv
move %fpath%attributes.csv %fpath%conf\attributes.csv
move %fpath%workload.csv %fpath%conf\workload.csv
if errorlevel 1 (GOTO END)

ECHO  - Step 3 - Creating Manifest
call "%CIRBA_HOME%\bin\audit-converter.bat" -m %fpath%conf\ "GCP"
if errorlevel 1 (GOTO END)

ECHO  - Step 4 - Creating Repository
call "%CIRBA_HOME%\bin\audit-converter.bat" %fpath%conf\ %fpath%repo\
if errorlevel 1 (GOTO END)

ECHO  - Step 5 - Loading Repository
call "%CIRBA_HOME%\bin\load-repository.bat" %fpath%repo\ -o
if errorlevel 1 (GOTO END)

ECHO  - Step 6 - Import Attributes
call "%CIRBA_HOME%\bin\data-tools.bat" ImportAttributes -f %fpath%conf\
if errorlevel 1 (GOTO END)

:END
PAUSE
