"""
conftest.py — pytest configuration for integration tests.

Sets RAAJADHARMA_GROUPS_ROOT to a writable temp path so that
importing app.py in tests doesn't trigger a PermissionError on /var.
"""
import os
import tempfile

# Set before any module-level imports from the integration backend
_TMPDIR = tempfile.mkdtemp(prefix="raajadharma-test-")
os.environ.setdefault("RAAJADHARMA_GROUPS_ROOT", _TMPDIR)
