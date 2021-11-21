@echo off
set "PYTHONPATH=%cd%;%PYTHONPATH%"
set "MAYA_SCRIPT_PATH=%cd%;%MAYA_SCRIPT_PATH%"
cpenv activate maya mtoa hotline
