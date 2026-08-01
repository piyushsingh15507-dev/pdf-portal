@echo off
echo ========================================================
echo   Creating portal_files.zip for 1-Click GitHub Upload
echo ========================================================

powershell -Command "Compress-Archive -Path 'server.py', 'student.html', 'student_style.css', 'student_script.js', 'admin.html', 'admin_style.css', 'admin_script.js', 'database.json' -DestinationPath 'portal_files.zip' -Force"

echo.
echo SUCCESS! Created 'portal_files.zip' in your folder:
echo %cd%\portal_files.zip
echo.
echo Next Steps:
echo 1. Open GitHub.com in your browser.
echo 2. Drag and drop 'portal_files.zip' or its files into your repository!
echo.
pause
