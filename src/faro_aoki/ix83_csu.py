"""Olympus IX83 with a Yokogawa CSU-W1 spinning disk.

Hardware: Olympus IX83 stand (turrets, ZDC, DIA2 halogen), Yokogawa CSU-W1
(filter wheel, dichroic, bright-field bypass, disk drive), Hamamatsu Orca
Fusion BT camera, SigmaKoki XY stage, Mightex Polygon DMD.

Excitation: Coherent OBIS lasers 445/488/561/640. They are not in
Micro-Manager; users switch the laser they need on the OBIS remote. Each
laser has a mechanical shutter, opened by an NI-DAQ TTL line through the
``LaserShutter`` State Device Shutter (100 ms delay). So no channel has a
software-set power, and ``POWER_PROPERTIES`` is empty: use plain ``Channel``,
not ``PowerChannel``.

DMD: a CoolLED lights the Polygon. How it is switched (for example by a camera
timing output) is still open.

Two classes share ``ix83csu.cfg`` (the DMD is always connected):

- ``IX83CSU``: the DMD shows all pixels on and is not calibrated. Whole-FOV
  stimulation (``StimWholeFOV``) is a plain channel preset, no custom MDA:
  ``DMD`` (CoolLED through the all-on DMD) or a laser preset through the CSU,
  for example ``GFP`` for 488 nm.
- ``IX83CSUDMD``: adds faro's DMD for patterned stimulation; run
  ``mic.calibrate_dmd(Channel("DMD", exposure=...))`` before a stim experiment.
"""

from importlib.resources import files

import pymmcore_plus

from faro.core.dmd import DMD
from faro.microscope.pymmcore import (
    ConfigGroupControl,
    ContinuousFocusControl,
    PyMMCoreMicroscope,
)

# Halogen lamp of the transmitted light path (DIA2), Brightness 0-255.
HALOGEN = "TransmittedIllumination 2"


class IX83CSU(PyMMCoreMicroscope):
    """IX83 CSU-W1; the DMD shows all pixels on (whole-FOV stimulation)."""

    MICROMANAGER_PATH = "C:\\Program Files\\Micro-Manager-2.0_api75"
    # Shipped with the package.
    MICROMANAGER_CONFIG = str(files("faro_aoki") / "configs" / "ix83csu.cfg")
    CHANNEL_GROUP = "Channel"
    USE_AUTOFOCUS_EVENT = False
    USE_ONLY_PFS = False

    # The "Illumination Control" dock of faro-napari, top to bottom (see
    # PyMMCoreMicroscope.NAPARI_CONTROLS for the entry types). The halogen
    # is set to one brightness per experiment; BF and DIC differ by exposure
    # time. The ZDC is the "Autofocus" device of the IX83 adapter.
    NAPARI_CONTROLS = [
        "Light",
        (HALOGEN, "Brightness", "Halogen"),
        "Spinning disk",
        ConfigGroupControl("CSU"),
        "Camera",
        ConfigGroupControl("Binning"),
        "Focus",
        ContinuousFocusControl("ZDC"),
    ]

    # Laser power is set by hand on the OBIS remote, the CoolLED on its own
    # controller: nothing to map.
    POWER_PROPERTIES: dict[str, tuple[str, str]] = {}

    def __init__(
        self,
        micromanager_path: str | None = None,
        config: str | None = None,
    ):
        super().__init__()
        self.micromanager_path = micromanager_path or self.MICROMANAGER_PATH
        self.micromanager_config = config or self.MICROMANAGER_CONFIG
        pymmcore_plus.use_micromanager(self.micromanager_path)
        self.mmc = pymmcore_plus.CMMCorePlus()
        self.slm_dev = None
        self.slm_width = None
        self.slm_height = None
        self.init_scope()

    def init_scope(self):
        """Load the config, apply startup, show all DMD pixels on, set the channel group."""
        self.mmc.loadSystemConfiguration(self.micromanager_config)
        self.mmc.setConfig("System", "Startup")
        self.slm_dev = self.mmc.getSLMDevice()
        if self.slm_dev:
            self.slm_width = self.mmc.getSLMWidth(self.slm_dev)
            self.slm_height = self.mmc.getSLMHeight(self.slm_dev)
            self.mmc.setSLMPixelsTo(self.slm_dev, 255)
            self.mmc.displaySLMImage(self.slm_dev)
        self.mmc.setChannelGroup(self.CHANNEL_GROUP)


class IX83CSUDMD(IX83CSU):
    """IX83 CSU-W1 with patterned DMD stimulation (faro's ``DMD``)."""

    def __init__(
        self,
        micromanager_path: str | None = None,
        config: str | None = None,
        affine_calibration_matrix=None,
    ):
        super().__init__(micromanager_path=micromanager_path, config=config)
        self.dmd = DMD(
            self.mmc,
            resolve_power=self.resolve_power,
            affine_matrix=affine_calibration_matrix,
        )
