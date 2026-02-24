"""PyInstaller hook for uvicorn — ensure all loop implementations are included."""

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("uvicorn")
