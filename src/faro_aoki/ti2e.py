"""Nikon Ti2-E with a Hamamatsu camera.

Hardware: Nikon Ti2-E stand (nosepiece, turrets, filter wheel, PFS, XY
stage, DiaLamp), X-Cite XT600 LED for epifluorescence, Hamamatsu DCAM
camera. Uses the default pymmcore-plus MDA engine.

No DMD: stimulation is whole-FOV only (``StimWholeFOV``), through a
fluorescence preset such as ``GFP`` for blue light.
"""

from importlib.resources import files

import pymmcore_plus

from faro.microscope.pymmcore import (
    ContinuousFocusControl,
    PyMMCoreMicroscope,
)
from faro_aoki._config import load_system_configuration


class Ti2E(PyMMCoreMicroscope):
    MICROMANAGER_PATH = "C:\\Program Files\\Micro-Manager-2.0_api75"
    # Shipped with the package.
    MICROMANAGER_CONFIG = str(files("faro_aoki") / "configs" / "NikonTi2e.cfg")
    CHANNEL_GROUP = "Channel"
    USE_AUTOFOCUS_EVENT = True
    USE_ONLY_PFS = False

    # Toolbar buttons of the pertzlab pymmcore-widgets build in faro-napari
    # (see PyMMCoreMicroscope.NAPARI_WIDGETS).
    NAPARI_WIDGETS = ["Stage Map"]

    # The "Illumination Control" dock of faro-napari, top to bottom (see
    # PyMMCoreMicroscope.NAPARI_CONTROLS for the entry types). The condenser
    # is set once per objective here when the "Channel" group is used: the
    # "Channel_w_condenser" presets set it themselves.
    NAPARI_CONTROLS = [
        "Light",
        ("LED1 Device", "L.15 Intensity", "LedEpi"),
        ("DiaLamp", "Intensity", "DiaLamp"),
        "Transmitted path",
        ("CondenserTurret", "Label", "Condenser"),
        "Filters",
        ("FilterTurret1", "Label", "Dichroic"),
        ("FilterWheel1", "Label", "Filter wheel"),
        "Camera",
        ("Camera", "Binning", "Binning"),
        ("Camera", "ScanMode", "ScanMode (1 sensitive, 3 fast)"),
        "Focus",
        ContinuousFocusControl("PFS"),
    ]

    # Fluorescence presets of the Channel and Channel_w_condenser groups. The
    # XT600 LED is their shutter, and the power of a PowerChannel (percent)
    # sets its intensity. DIC and QPI use the DiaLamp and take no power.
    LED_CHANNELS = (
        "DAPI",
        "405ex520em",
        "CFP(FRET)",
        "YFP(FRET)",
        "GFP",
        "YFP_Custom",
        "RFP",
        "iRFP",
    )
    LED_DEVICE = "LED1 Device"
    # The adapter builds this name at runtime from the LED's minimum, for
    # example "L.15 Intensity (0.0 or 5.0 - 100.0)%", so it is matched by
    # prefix. The LED accepts 0 or a value from that minimum to 100.
    LED_INTENSITY_PREFIX = "L.15 Intensity"

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
        self.init_scope()

    def init_scope(self):
        """Load the config, apply the startup preset, set the channel group."""
        load_system_configuration(self.mmc, self.micromanager_config)
        self.mmc.setConfig("System", "Startup")
        self.mmc.setChannelGroup(self.CHANNEL_GROUP)
        self.POWER_PROPERTIES = self._led_power_properties()

    def _led_power_properties(self) -> dict[str, tuple[str, str]]:
        """Map every LED preset to the LED's intensity property."""
        names = self.mmc.getDevicePropertyNames(self.LED_DEVICE)
        prop = next((p for p in names if p.startswith(self.LED_INTENSITY_PREFIX)), None)
        if prop is None:
            raise RuntimeError(
                f"{self.LED_DEVICE!r} has no property starting with "
                f"{self.LED_INTENSITY_PREFIX!r}. Properties: {', '.join(names)}"
            )
        return {config: (self.LED_DEVICE, prop) for config in self.LED_CHANNELS}

    def post_experiment(self):
        pass
