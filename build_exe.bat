@echo off
REM =========================================================================
REM  FileSense Desktop Application - Build Script
REM  
REM  This script builds FileSense into a distributable Windows application.
REM  
REM  Prerequisites:
REM    1. Python 3.11+ installed and on PATH
REM    2. All dependencies installed: pip install -r requirements.txt
REM    3. sentence-transformers model pre-downloaded (see Step 1 below)
REM  
REM  Usage:
REM    build_exe.bat
REM  
REM  Output:
REM    dist\FileSense\FileSense.exe
REM =========================================================================

echo.
echo ===================================================
echo   FileSense Desktop Application Builder
echo ===================================================
echo.

REM -----------------------------------------------------------------------
REM  Step 1: Pre-download the sentence-transformers model
REM -----------------------------------------------------------------------
echo [1/4] Pre-downloading sentence-transformers model...
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to download the embedding model.
    echo Make sure sentence-transformers is installed: pip install sentence-transformers
    pause
    exit /b 1
)
echo       Model downloaded successfully.
echo.

REM -----------------------------------------------------------------------
REM  Step 2: Verify pywebview is installed
REM -----------------------------------------------------------------------
echo [2/4] Verifying pywebview installation...
python -c "import webview; print('pywebview installed successfully')"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: pywebview is not installed.
    echo Install it with: py -m pip install pywebview
    pause
    exit /b 1
)
echo       pywebview verified.
echo.

REM -----------------------------------------------------------------------
REM  Step 3: Clean previous builds
REM -----------------------------------------------------------------------
echo [3/4] Cleaning previous build artifacts...
if exist "build" rmdir /s /q "build"
if exist "dist\FileSense" rmdir /s /q "dist\FileSense"
echo       Clean complete.
echo.

REM -----------------------------------------------------------------------
REM  Step 4: Run PyInstaller
REM -----------------------------------------------------------------------
echo [4/4] Building executable with PyInstaller...
echo       This may take 5-15 minutes depending on your system.
echo.
pyinstaller filesense.spec --noconfirm
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: PyInstaller build failed. Check the output above for details.
    pause
    exit /b 1
)

echo.
echo ===================================================
echo   BUILD SUCCESSFUL!
echo ===================================================
echo.
echo   Output: dist\FileSense\FileSense.exe
echo.
echo   To test: run dist\FileSense\FileSense.exe
echo   To distribute: zip the entire dist\FileSense\ folder
echo.
echo   NOTE: The dist\FileSense\ folder must be kept intact.
echo   All files in that folder are required for the app to run.
echo.
pause
