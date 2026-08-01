@echo off
echo ===================================================
echo   Uploading Classplus PDF Portal to GitHub
echo ===================================================

set PATH=C:\Program Files\Git\cmd;%PATH%

cd /d "c:\Users\HP\Downloads\hls live classplus"

git config user.email "piyushsingh15507@gmail.com"
git config user.name "piyushsingh15507-dev"

git init
git add .
git commit -m "Initial Classplus PDF Portal Release"
git branch -M main

git remote remove origin 2>nul
git remote add origin https://github.com/piyushsingh15507-dev/pdf-portal.git

git push -u origin main

echo.
echo Upload completed!
pause
