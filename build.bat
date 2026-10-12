@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

rem ============================================================
rem  FlowLedger one-click build script
rem  Creates an isolated conda environment, installs
rem  dependencies via pip, and packages a single-file
rem  FlowLedger.exe.
rem ============================================================

set ENV_NAME=flowledger
set PY_VERSION=3.11

cd /d "%~dp0"

echo [1/5] 检查 conda 环境...
where conda >nul 2>nul
if errorlevel 1 (
    echo 错误：未找到 conda，请先安装 Miniconda/Anaconda 并确保已加入 PATH。
    pause
    exit /b 1
)

conda env list | findstr /r /c:"^%ENV_NAME% " >nul 2>nul
if errorlevel 1 (
    echo [2/5] 创建 conda 环境 %ENV_NAME%（Python %PY_VERSION%）...
    call conda create -n %ENV_NAME% python=%PY_VERSION% -y
    if errorlevel 1 (
        echo 错误：创建 conda 环境失败。
        pause
        exit /b 1
    )
) else (
    echo [2/5] 已检测到 conda 环境 %ENV_NAME%，跳过创建。
)

echo [3/5] 安装依赖（PySide6 / Pillow / openpyxl / RapidOCR / PyInstaller，通过 pip 安装）...
call conda run -n %ENV_NAME% --no-capture-output python -m pip install --upgrade pip
call conda run -n %ENV_NAME% --no-capture-output python -m pip install -r requirements.txt
if errorlevel 1 (
    echo 错误：依赖安装失败。
    pause
    exit /b 1
)

echo [4/5] 使用 PyInstaller 打包单文件 exe（包含 OCR 模型，体积较大，请耐心等待）...
set ICON_ARG=
set DATA_ARG=
if exist "favicon.ico" (
    set ICON_ARG=--icon "favicon.ico"
    rem also bundle it so the running window / taskbar can show the same icon
    set DATA_ARG=--add-data "favicon.ico;."
)

call conda run -n %ENV_NAME% --no-capture-output python -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name FlowLedger ^
    --paths src ^
    --collect-all rapidocr_onnxruntime ^
    --collect-all pillow_heif ^
    --exclude-module PySide6.QtWebEngineCore ^
    --exclude-module PySide6.QtWebEngineWidgets ^
    %DATA_ARG% ^
    %ICON_ARG% ^
    "src\main.py"
if errorlevel 1 (
    echo 错误：PyInstaller 打包失败。
    pause
    exit /b 1
)

echo [5/5] 整理输出文件...
if not exist "release" mkdir "release"
copy /y "dist\FlowLedger.exe" "release\FlowLedger.exe" >nul

echo.
echo ============================================================
echo  打包完成！可执行文件位于：release\FlowLedger.exe
echo ============================================================

set /p OPEN_FOLDER=是否在文件资源管理器中打开该文件夹？(Y/N): 
if /i "%OPEN_FOLDER%"=="Y" (
    explorer "%~dp0release"
)

pause
