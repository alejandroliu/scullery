@echo off
setlocal
if EXIST %~dp0%env.bat (
  call %~dp0%env.bat 
)
if EXIST %~dp0%..\env.bat (
  call %~dp0%..\env.bat
)
set PYTHONPATH=%PYTHONPATH%;%~dp0
if NOT "%proxy"=="" (
  set http_proxy=http://%proxy%/
  set https_proxy=http://%proxy%/
  set pipproxy=--proxy=%proxy%
) else (
  set pipproxy=
)
set VENV=%~dp0.venv
call %VENV%\Scripts\activate.bat

python.exe -m scullery %*

