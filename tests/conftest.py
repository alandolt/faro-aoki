"""pytest configuration of faro-aoki.

``faro.testing.plugin`` adds ``--scope`` (``ix83unit2``, ``ti2e``), the
``hardware`` marker and the generic fixtures (``microscope``,
``safe_positions``, ``cellpose_segmentator``, ...). Hardware tests go to
``tests/hardware/``; without ``--scope`` or ``FARO_SCOPE`` they are skipped.
"""

pytest_plugins = ["faro.testing.plugin"]
