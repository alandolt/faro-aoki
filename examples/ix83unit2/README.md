# Examples for the Olympus IX83 unit 2

The Pertzlab example experiments, adapted to the IX83 unit 2 (IX83-弐号機) of
the Aoki lab (`faro_aoki.ix83_unit2.IX83Unit2`, config `IX83Unit2.cfg`).

| Folder | What it shows | Needs the IX83 |
|--------|---------------|----------------|
| `01_simple_acquisition/` | A first timelapse at one stage position, with napari-micromanager for live view and stage control: Cellpose (or Otsu) segmentation and tracking, no stimulation. | yes |
| `02_multi_position/` | The same timelapse at several fields of view, picked in the MDA widget of napari-micromanager and read with `generate_fov_positions`. | yes |
| `03_demo_writer_implementation/` | The same short experiment with `TiffWriter`, `OmeZarrWriter` and `OmeZarrWriterPlate`, and the conversion of a TIFF run to OME-Zarr. | yes, except the conversion |
| `04_erk_experiments_full_fov_stim/` | ERK-KTR experiments with whole-FOV blue light, built with `RTMSequence`. | yes |
| `05_reanalysis/` | Re-processing a finished run offline with new tracking or features. | no |

## Before a run

- Every notebook writes its data into a `data/` folder next to it (ignored by git).
- Close MetaMorph and any other Micro-Manager: a device can be opened by one program only.
- The notebooks open napari with napari-micromanager themselves (`open_napari`). Do not run `faro-napari ix83unit2` at the same time.
- Positions built from the current stage position carry no `z`, so faro never moves the focus drive.

## IX83 unit 2 specifics

- **No DMD.** Stimulation is whole-FOV only (`StimWholeFOV`), with the cyan LED of the `GFP` preset as blue light.
- **One Spectra LED per preset.** The Lumencor Spectra X is the shutter of every fluorescence preset, and each preset turns on one of its LEDs. `IX83Unit2.POWER_PROPERTIES` maps the preset to that LED's level (0-99), so `PowerChannel(config=..., power=...)` sets it.
- **Give every fluorescence channel a power.** The presets store none, so a channel without a power uses the level the LED had last (99 after the Spectra powers on). Use `PowerChannel` with `group=mic.CHANNEL_GROUP` also for stim and ref channels: a plain dict there loses its `power`.
- **Transmitted light takes no power.** The `Trans_*` presets use the halogen lamp. Set its brightness once (Halogen slider of the Illumination Control dock); a `Trans_*` channel with a power raises an error.
- **PVCAM camera.** The camera hands out each snapped frame only once. `open_napari(mic)` and `faro-napari ix83unit2` install a cache so napari-micromanager can read it twice. Stop **Live** before a snap or a run.
- **Focus.** The ZDC is the continuous focus (`ZDC` toggle in the Illumination Control dock).
- **Preset mapping from the Pertzlab scopes:** `miRFP` is `iRFP`, `mScarlet3` is `RFP`, `CyanStim` is `GFP`, `mCitrine` is `YFP`. The `_glass` presets use a BK7 glass plate instead of the Di01 dichroic in Dichroic 2; the examples use the plain presets.
