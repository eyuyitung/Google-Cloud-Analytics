@ECHO OFF

rem ***************** set these parameters ********************

rem one week is 168 hours, month is 720 hours, cannot sample beyond 6 weeks (1008 hours)
set HOURS=168 

rem within the project specified do any of the instances contain active stackdriver agents? (Y/N)
set AGENTS=N

rem **************** edit nothing beyond this point *********************


echo Copyright (c) 2002-2017 Cirba Inc. D/B/A Densify. All Rights Reserved.
set /p PROJECT_ID=Please enter full credential file name: (ex. my-project-123.json) 

set fpath=%~sdp0

ECHO  - Step 1 - GCP Discovery

py %fpath%src\main.py -a %AGENTS% -t %HOURS% -i %PROJECT_ID%

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