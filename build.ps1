python -m pip install pyinstaller
pyinstaller `
  --noconfirm `
  --onedir `
  --name canvas-bulk-panel `
  --add-data "templates;templates" `
  --add-data "static;static" `
  app.py
