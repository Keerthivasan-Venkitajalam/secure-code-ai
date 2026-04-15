# Package SecureCodeAI Extension
Write-Host "Compiling TypeScript..." -ForegroundColor Cyan
npx tsc

Write-Host "`nPackaging extension..." -ForegroundColor Cyan
npx vsce package --allow-missing-repository --out securecodai-0.1.0.vsix

Write-Host "`nDone! Extension packaged as securecodai-0.1.0.vsix" -ForegroundColor Green
Write-Host "`nTo install:" -ForegroundColor Yellow
Write-Host "1. Open VS Code" -ForegroundColor Yellow
Write-Host "2. Press Ctrl+Shift+X (Extensions)" -ForegroundColor Yellow
Write-Host "3. Click '...' menu -> Install from VSIX..." -ForegroundColor Yellow
Write-Host "4. Select securecodai-0.1.0.vsix" -ForegroundColor Yellow
