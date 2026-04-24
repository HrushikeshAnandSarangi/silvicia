# Start Script for QGIS Demo Backend & Workers

Write-Host "Starting Daphne WebSocket + HTTP Server on Port 8000..." -ForegroundColor Cyan
Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", "cd c:\Users\hrush\OneDrive\Desktop\qgis_demo; .\venv\Scripts\activate; daphne -b 0.0.0.0 -p 8000 qgis_backend.asgi:application"

Write-Host "Starting Mock Task Workers..." -ForegroundColor Green
Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", "cd c:\Users\hrush\OneDrive\Desktop\qgis_demo; .\venv\Scripts\activate; python manage.py runworkers"

Write-Host "Both systems started! Proceed to http://localhost:8000" -ForegroundColor Yellow
