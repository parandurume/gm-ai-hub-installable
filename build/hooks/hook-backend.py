"""PyInstaller hook for backend — collect all backend submodules."""

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("backend")
