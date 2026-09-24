# =======================================================
# Quick Panel - Automated Windows Installer
# Multi-Platform UI Environment for Windows
# =======================================================
$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting Quick Panel Installation for Windows..." -ForegroundColor Cyan

# 1. Check Python
try {
    $pythonVer = python --version 2>&1
    Write-Host "✅ Found Python: $pythonVer" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Python not found in PATH. Please install Python 3.10+ from python.org or Microsoft Store." -ForegroundColor Red
    Exit 1
}

# 2. Install Dependencies
Write-Host "📦 Installing Python dependencies for Windows..." -ForegroundColor Yellow
python -m pip install --upgrade pip
python -m pip install pygobject pycaw comtypes winsdk pillow pystray

# 3. Target Install Directory
$installDir = "$env:LOCALAPPDATA\QuickPanel"
if (-not (Test-Path $installDir)) {
    New-Item -ItemType Directory -Path $installDir -Force | Out-Null
}

Write-Host "📂 Copying application files to $installDir..." -ForegroundColor Yellow

# Copy src and widgets
Copy-Item -Path "src\*" -Destination $installDir -Recurse -Force

# 4. Create VBS Launcher for Silent Startup
$vbsContent = @"
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "pythonw """ & "$installDir\quick-panel.py" & """", 0, False
WshShell.Run "pythonw """ & "$installDir\widgets\quick-osd.py" & """", 0, False
"@

$vbsPath = "$installDir\start-quick-panel.vbs"
Set-Content -Path $vbsPath -Value $vbsContent

# 5. Create Windows Startup Shortcut
$startupDir = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$shortcutPath = "$startupDir\QuickPanel.lnk"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($shortcutPath)
$Shortcut.TargetPath = "wscript.exe"
$Shortcut.Arguments = """$vbsPath"""
$Shortcut.WorkingDirectory = $installDir
$Shortcut.Description = "Quick Panel Windows Startup"
$Shortcut.Save()

Write-Host "🔁 Created Windows Startup shortcut: $shortcutPath" -ForegroundColor Green

# 6. Launch Quick Panel
Write-Host "⚡ Launching Quick Panel..." -ForegroundColor Cyan
Start-Process -FilePath "wscript.exe" -ArgumentList """$vbsPath"""

Write-Host ""
Write-Host "🎉 Quick Panel Windows Installation Complete!" -ForegroundColor Green
Write-Host "   Quick Panel will run automatically every time Windows starts." -ForegroundColor White
