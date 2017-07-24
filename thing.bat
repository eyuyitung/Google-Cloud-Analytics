ECHO OFF

SETLOCAL

ECHO  - Step 1 - AWS Discovery
python %~dp0src\main.py

ECHO  - Step 2 - GCP Config
move %~dp0gcp_config.csv %~dp0conf\gcp_config.csv
move %~dp0attributes.csv %~dp0conf\attributes.csv

ECHO  - Step 3 - Creating Manifest
call "%CIRBA_HOME%\bin\audit-converter.bat" -m %~dp0conf\ "GCP"

ECHO  - Step 4 - Creating Repository
call "%CIRBA_HOME%\bin\audit-converter.bat" %~dp0conf\ %~dp0repo\
ENDLOCAL
PAUSE