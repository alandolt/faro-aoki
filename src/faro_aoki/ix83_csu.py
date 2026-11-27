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

Mightex Polygon400 SDK: ``MT_Polygon400_SDK.dll`` must be in the Micro-Manager
folder. The SDK also needs the ``MT_Polygon400_SDK`` folder (from the PolyScan2
installer, it holds one ``<device>.dcg`` file per Polygon) in the current
working directory: it looks there when its DLL is loaded and creates an empty
folder if missing. Without the ``.dcg`` file, ``MTPLG_InitDevice`` returns -3
and the adapter fails with "Unable to communicate with the device" (35). The
Micro-Manager GUI runs in its own folder, so it finds
``C:\\Program Files\\Micro-Manager-2.0\\MT_Polygon400_SDK\\``; faro does not.
Put the folder in both places: the Micro-Manager folder (for the GUI) and the
folder faro is started from. Tested on the microscope
with the offline Windows 7 bundle: copying ``MT_Polygon400_SDK`` into
``C:\\faro-aoki-w7`` (the working directory there) makes the Polygon work.

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
    ContinuousFocusControl,
    PropertyToggle,
    PyMMCoreMicroscope,
)
from faro_aoki._config import load_system_configuration

# Halogen lamp of the transmitted light path (DIA2), Brightness 0-255.
DIALAMP = "TransmittedIllumination 2"


class IX83CSU(PyMMCoreMicroscope):
    """IX83 CSU-W1; the DMD shows all pixels on (whole-FOV stimulation)."""

    MICROMANAGER_PATH = "C:\\Program Files\\Micro-Manager-2.0"
    # Shipped with the package.
    MICROMANAGER_CONFIG = str(files("faro_aoki") / "configs" / "ix83csu.cfg")
    CHANNEL_GROUP = "Channel"
    USE_AUTOFOCUS_EVENT = False
    USE_ONLY_PFS = False
    # Keep the ZDC on for the whole run instead of the MDA widget's hardware
    # autofocus settings: faro-napari hides them and keeps them off.
    HIDE_AUTOFOCUS = True
    NAPARI_INCLUDE_Z_TEXT = "Include Z (uncheck if AF is on)"

    # Toolbar buttons of the pertzlab pymmcore-widgets build in faro-napari
    # (see PyMMCoreMicroscope.NAPARI_WIDGETS).
    NAPARI_WIDGETS = ["Stage Map"]

    # Brightness (0-255) that the "Lamp on" check box of the faro-napari dock
    # sets when first ticked; later ticks restore the brightness at the last
    # untick (100 is about 5.5 V on the halogen).
    LAMP_ON_BRIGHTNESS = 120

    # The "Illumination Control" dock of faro-napari, top to bottom (see
    # PyMMCoreMicroscope.NAPARI_CONTROLS for the entry types). The halogen
    # is set to one brightness per experiment; BF and DIC differ by exposure
    # time. The ZDC is the "Autofocus" device of the IX83 adapter. The
    # "Channel" presets set the polarizer: In for all (DIC is the usual
    # transmitted image; fluorescence does not care), Out for Trans_BF and
    # Trans_BF_OptoBlue. The Polarizer row overrides it by hand.
    NAPARI_CONTROLS = [
        "Light",
        (DIALAMP, "Brightness", "DIALamp"),
        PropertyToggle(DIALAMP, "Brightness", LAMP_ON_BRIGHTNESS, "Lamp on"),
        "Transmitted path",
        ("Condenser turret", "Label", "Condenser"),
        ("Polarizer", "Label", "Polarizer"),
        "Spinning disk",
        ("CSUW1-Bright Field", "BrightFieldPort", "Brightfield/Confocal"),
        ("CSUW1-Drive Speed", "Run", "SpinningDisc On/Off"),
        ("CSUW1-Drive Speed", "State", "SpinningDisc Speed"),
        ("CSUW1-Aperture", "State", "CSU Aperture"),
        "Filters",
        ("Dichroic 1", "Label", "Mic-Dichroic 1"),
        ("Dichroic 2", "Label", "Mic-Dichroic 2"),
        ("CSUW1-Dichroic Mirror", "Label", "CSU-Dichroic"),
        ("CSUW1-Filter Wheel", "Label", "CSU-Filter Wheel"),
        "Camera",
        ("Camera", "Binning", "Binning"),
        ("Camera", "ScanMode", "ScanMode (1 sensitive, 3 fast)"),
        "Autofocus",
        ContinuousFocusControl("ZDC"),
        ("Autofocus", "LowerLimit", "ZDC lower limit"),
        ("Autofocus", "UpperLimit", "ZDC upper limit"),
        ("AutofocusDrive", "Offset", "ZDC offset"),
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
        # By hand, else MICROMANAGER_PATH, else the class's folder
        # (PyMMCoreMicroscope.micromanager_dir).
        self.micromanager_path = self.micromanager_dir(micromanager_path)
        self.micromanager_config = config or self.MICROMANAGER_CONFIG
        pymmcore_plus.use_micromanager(self.micromanager_path)
        self.mmc = pymmcore_plus.CMMCorePlus(self.micromanager_path)
        self.slm_dev = None
        self.slm_width = None
        self.slm_height = None
        self.init_scope()

    def init_scope(self):
        """Load the config, apply startup, show all DMD pixels on, set the channel group."""
        load_system_configuration(self.mmc, self.micromanager_config)
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
