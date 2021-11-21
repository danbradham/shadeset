@echo off
set "PYTHONPATH=%cd%;%PYTHONPATH%"
set "MAYA_SCRIPT_PATH=%cd%;%MAYA_SCRIPT_PATH%"
cpenv activate maya-2020.4 mtoa-4.2.2 hotline
