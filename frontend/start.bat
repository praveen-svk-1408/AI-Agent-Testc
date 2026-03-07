@echo off
echo Installing dependencies...
call npm install

echo.
echo Starting development server...
echo Frontend will be available at: http://localhost:3000
echo.
call npm run dev
