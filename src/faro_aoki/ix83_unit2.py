"""Olympus IX83 (IX83-弐号機, "unit no. 2") with a Teledyne PVCAM camera.

Hardware: Olympus IX83 stand (turrets, filter wheels, shutters, ZDC, XY
stage), Lumencor Spectra X light engine, Teledyne PVCAM camera (Sigma).

The Spectra is the core shutter for every fluorescence channel; the two
Olympus epi shutters stay open (the ``System/Startup`` preset opens them).

The PVCAM adapter hands out each snapped frame only once. Run the GUI
through ``faro-napari ix83_unit2``, which installs faro's snap cache. Plain
napari-micromanager reads every snap twice and shows "Camera image buffer
read failed" on the second read.
"""

import logging
from importlib.resources import files

import pymmcore_plus
from pymmcore_plus.mda import MDAEngine

from faro.microscope.pymmcore import ConfigGroupControl, PyMMCoreMicroscope

logger = logging.getLogger(__name__)

# Halogen lamp of the transmitted light path (DIA2).
HALOGEN = "TransmittedIllumination 2"


class IX83Unit2MDAEngine(MDAEngine):
    """MDA engine that stops live view before the run.

    The PVCAM adapter hands out each snapped frame only once. With live view
    still running when the first snap fires, napari-micromanager reads the
    frame first and the engine's ``getImage`` raises "Camera image buffer
    read failed". faro's Controller stops live itself; doing it here also
    covers napari-micromanager's MDA widget and bare ``mmc.mda.run()``.

    Not gated on ``isSequenceRunning()``: napari-micromanager can hold a live
    timer while the stream is already stopped, and the emitted
    ``sequenceAcquisitionStopped`` is what clears that timer.
    """

    def setup_sequence(self, sequence):
        try:
            self.mmcore.stopSequenceAcquisition()
        except Exception:
            logger.exception("Failed to stop live acquisition before MDA")
        return super().setup_sequence(sequence)


class IX83Unit2(PyMMCoreMicroscope):
    MICROMANAGER_PATH = "C:\\Program Files\\Micro-Manager-2.0"
    # Shipped with the package. Its presets are generated from MetaMorph's
    # illumination settings by tools/ix83_unit2/ils_to_mm_presets.py.
    MICROMANAGER_CONFIG = str(files("faro_aoki") / "configs" / "IX83Lumencor2.cfg")
    CHANNEL_GROUP = "Channel"
    # The "Illumination Control" dock of faro-napari, top to bottom (see
    # PyMMCoreMicroscope.NAPARI_CONTROLS for the entry types). The ZDC is the
    # "Autofocus" device; the cfg does not set it as the core's autofocus
    # device, so it is switched through its ZDCEnabled property rather than a
    # ContinuousFocusControl.
    NAPARI_CONTROLS = [
        "Light",
        ("Spectra", "Violet_Level", "Violet (UV)"),
        ("Spectra", "Blue_Level", "Blue"),
        ("Spectra", "Cyan_Level", "Cyan"),
        ("Spectra", "Teal_Level", "Teal"),
        ("Spectra", "Green_Level", "Green"),
        ("Spectra", "Red_Level", "Red"),
        (HALOGEN, "Brightness", "Halogen"),
        "Camera",
        ConfigGroupControl("Binning"),
        "Focus",
        ("Autofocus", "ZDCEnabled", "ZDC"),
    ]
    USE_AUTOFOCUS_EVENT = False
    USE_ONLY_PFS = False

    # Channel preset -> (device, property) that sets the excitation power.
    # A PowerChannel whose config is missing here raises in resolve_power()
    # instead of silently dropping the requested power.
    #
    # Derived from the cfg: each fluorescence preset enables one Spectra LED
    # (<Color>_Enable = 1), and that LED's <Color>_Level (0-99) sets the
    # power. Comments give the emission filter (Filter Wheel 2).
    #
    # The Trans_* presets (transmitted light) are left out on purpose: the
    # halogen is set to one Brightness (0-255) at the start of the experiment
    # (Halogen slider in faro-napari, or mmc.setProperty(HALOGEN, "Brightness",
    # ...)) and stays there. BF and DIC differ by exposure time, not lamp
    # power, so the lamp is never changed per frame. A Trans_* channel given a
    # power raises in resolve_power(). The IX83 adapter has no lamp on/off;
    # System/Startup sets Brightness 0, so epi-only experiments stay dark.
    #
    # The cfg presets store no power on purpose: give every fluorescence
    # channel a power. Without one, the LED keeps the level last set (99
    # after the Spectra powers on).
    POWER_PROPERTIES = {
        # em 445/40
        "BFP": ("Spectra", "Violet_Level"),
        "BFP_glass": ("Spectra", "Violet_Level"),
        # em 483/32
        "CFP": ("Spectra", "Blue_Level"),
        "CFP_glass": ("Spectra", "Blue_Level"),
        "CFP_Di02": ("Spectra", "Blue_Level"),
        # em 520/28
        "405ex_520em": ("Spectra", "Violet_Level"),
        "BFP_pHluorin2": ("Spectra", "Violet_Level"),
        "BFP_pHluorin2_glass": ("Spectra", "Violet_Level"),
        "FRET": ("Spectra", "Blue_Level"),
        "FRET_glass": ("Spectra", "Blue_Level"),
        "FRET_Di02": ("Spectra", "Blue_Level"),
        "GFP": ("Spectra", "Cyan_Level"),
        "GFP_glass": ("Spectra", "Cyan_Level"),
        "GFP_QUEEN": ("Spectra", "Violet_Level"),
        "GFP_QUEEN_glass": ("Spectra", "Violet_Level"),
        "YFP": ("Spectra", "Green_Level"),
        # em 563/9
        "GFP_KO_FRET_glass": ("Spectra", "Cyan_Level"),
        "KO": ("Spectra", "Green_Level"),
        "KO_glass": ("Spectra", "Green_Level"),
        # em 641/75
        "GFPex_RFPem": ("Spectra", "Cyan_Level"),
        "RFP": ("Spectra", "Green_Level"),
        "RFP_glass": ("Spectra", "Green_Level"),
        # em 664 long-pass
        "iRFP": ("Spectra", "Red_Level"),
        "iRFP_glass": ("Spectra", "Red_Level"),
        "iRFP_Di02": ("Spectra", "Red_Level"),
        "Photoconversion_UV": ("Spectra", "Violet_Level"),
    }
    # Preset of the cfg's "Binning" group ("1x1" or "2x2"), set at startup.
    BINNING = "1x1"
    # ROI applied as-is after binning, no centering recomputation. Off by
    # default (full sensor); set SET_ROI_REQUIRED and the ROI_* values, in
    # binned pixels, to crop.
    ROI_X = 0
    ROI_Y = 0
    ROI_WIDTH: int | None = None
    ROI_HEIGHT: int | None = None
    SET_ROI_REQUIRED = False

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
        self.init_scope()

    def init_scope(self):
        """Load the config, apply startup, binning and ROI, set the channel group."""
        self.mmc.loadSystemConfiguration(self.micromanager_config)
        self.mmc.setConfig("System", "Startup")
        # Pin camera binning before set_roi(): MM camera drivers reset
        # the ROI on a binning change, so binning must come first.
        self.mmc.setConfig("Binning", self.BINNING)
        if self.SET_ROI_REQUIRED:
            self.set_roi()
        self.mmc.setChannelGroup(self.CHANNEL_GROUP)
        self.engine = IX83Unit2MDAEngine(self.mmc)
        self.mmc.mda.set_engine(self.engine)

    def set_roi(self):
        """Apply the class's ROI_* settings as-is (after binning is set)."""
        if self.ROI_WIDTH is None or self.ROI_HEIGHT is None:
            raise ValueError(
                f"{type(self).__name__}.SET_ROI_REQUIRED is True but "
                "ROI_WIDTH/ROI_HEIGHT are not set."
            )
        self.mmc.clearROI()
        self.mmc.setROI(self.ROI_X, self.ROI_Y, self.ROI_WIDTH, self.ROI_HEIGHT)

    def post_experiment(self):
        pass
