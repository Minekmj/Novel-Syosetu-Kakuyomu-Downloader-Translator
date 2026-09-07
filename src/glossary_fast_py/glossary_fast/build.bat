@echo off
chcp 65001 >nul
cl /nologo /O2 /LD /utf-8 glossary_fast.c /Fe:glossary_fast.dll
if errorlevel 1 (
    echo BUILD FAILED
    pause
    exit /b 1
)
echo BUILD SUCCESS
pause