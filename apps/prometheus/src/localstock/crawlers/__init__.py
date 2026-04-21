"""Data crawlers for vnstock and external sources.

Provides ``suppress_vnstock_output()`` context manager to silence
vnstock's intrusive advertising banner on stdout.
"""

import contextlib
import io
import os
import sys


@contextlib.contextmanager
def suppress_vnstock_output():
    """Suppress vnstock's advertising banner from stdout.

    vnstock 3.5.x prints a large INSIDERS PROGRAM banner to stdout
    on first import/call. This redirects stdout to devnull during
    vnstock operations.
    """
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        yield
    finally:
        sys.stdout = old_stdout
