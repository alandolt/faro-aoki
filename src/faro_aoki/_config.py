"""Load a Micro-Manager config with a readable error on a non-English Windows."""

import sys


def load_system_configuration(mmc, config: str) -> None:
    """Call ``mmc.loadSystemConfiguration(config)``.

    When a device adapter fails to load, the MMCore error contains the
    Windows message (e.g. "The specified module could not be found"). Windows
    writes it in the system code page, cp932 on a Japanese Windows. pymmcore
    decodes the error as UTF-8 and raises ``UnicodeDecodeError`` instead,
    which hides the message. Here the raw bytes are decoded in the system
    code page and raised as a ``RuntimeError``.
    """
    try:
        mmc.loadSystemConfiguration(config)
    except UnicodeDecodeError as e:
        encoding = "mbcs" if sys.platform == "win32" else "latin-1"
        message = e.object.decode(encoding, errors="replace")
        raise RuntimeError(
            f"Failed to load the Micro-Manager config {config}:\n{message}"
        ) from None
