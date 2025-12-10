@echo off
REM GhostQA Cache Cleanup Script for Windows
REM Removes all cache files and directories from the project

echo ========================================
echo   GhostQA Cache Cleanup
echo ========================================
echo.

cd /d "%~dp0"
echo Working directory: %CD%
echo.

REM 1. Python cache directories
echo [1/6] Removing Python __pycache__ directories...
for /d /r %%d in (__pycache__) do (
    if exist "%%d" (
        echo   Removing: %%d
        rd /s /q "%%d" 2>nul
    )
)

REM 2. Python compiled files
echo.
echo [2/6] Removing .pyc and .pyo files...
del /s /q *.pyc 2>nul
del /s /q *.pyo 2>nul
del /s /q *.pyd 2>nul
echo   Done

REM 3. Pytest cache
echo.
echo [3/6] Removing pytest cache...
for /d /r %%d in (.pytest_cache) do (
    if exist "%%d" (
        echo   Removing: %%d
        rd /s /q "%%d" 2>nul
    )
)
for /d /r %%d in (.mypy_cache) do (
    if exist "%%d" (
        echo   Removing: %%d
        rd /s /q "%%d" 2>nul
    )
)

REM 4. Node.js cache
echo.
echo [4/6] Removing Node.js cache...
if exist "frontend\node_modules\.cache" (
    echo   Removing: frontend\node_modules\.cache
    rd /s /q "frontend\node_modules\.cache" 2>nul
)
if exist "frontend\.vite" (
    echo   Removing: frontend\.vite
    rd /s /q "frontend\.vite" 2>nul
)

REM 5. Build artifacts
echo.
echo [5/6] Removing build artifacts...
if exist "frontend\dist" (
    echo   Removing: frontend\dist
    rd /s /q "frontend\dist" 2>nul
)
if exist "backend\build" (
    echo   Removing: backend\build
    rd /s /q "backend\build" 2>nul
)
for /d /r %%d in (*.egg-info) do (
    if exist "%%d" (
        echo   Removing: %%d
        rd /s /q "%%d" 2>nul
    )
)

REM 6. Misc cache files
echo.
echo [6/6] Removing miscellaneous cache files...
del /s /q Thumbs.db 2>nul
for /d /r %%d in (.ruff_cache) do (
    if exist "%%d" (
        echo   Removing: %%d
        rd /s /q "%%d" 2>nul
    )
)

echo.
echo ========================================
echo   Cache cleanup complete!
echo ========================================
echo.
echo Note: To also clear the knowledge base cache, run:
echo   rd /s /q backend\app\data\agent_knowledge\cache
echo.

pause
