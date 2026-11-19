# Examples for the Nikon Ti2-E

The Pertzlab example experiments, adapted to the Ti2-E of the Aoki lab
(`faro_aoki.ti2e.Ti2E`, config `NikonTi2e.cfg`).

| Folder | What it shows | Needs the Ti2-E |
|--------|---------------|-----------------|
| `01_simple_acquisition/` | A first timelapse at one stage position, with napari-micromanager for live view and stage control: Cellpose (or Otsu) segmentation and tracking, no stimulation. | yes |
| `02_multi_position/` | The same timelapse at several fields of view, picked in the MDA widget of napari-micromanager and read with `generate_fov_positions`. | yes |
| `03_demo_writer_implementation/` | The same short experiment with `TiffWriter`, `OmeZarrWriter` and `OmeZarrWriterPlate`, and the conversion of a TIFF run to OME-Zarr. | yes, except the conversion |
| `04_erk_experiments_full_fov_stim/` | ERK-KTR experiments with whole-FOV blue light, built with `RTMSequence`. | yes |
| `05_reanalysis/` | Re-processing a finished run offline with new tracking or features. | no |

## Before a run

- Every notebook writes its data into a `data/` folder next to it (ignored by git).

- Close NIS-Elements and any other Micro-Manager: a device can be opened by one program only.
- The notebooks open napari with napari-micromanager themselves. Do not run `faro-napari ti2e` at the same time.
- Positions built from the current stage position carry no `z`, so faro never moves the focus drive.

## Ti2-E specifics

- **No DMD.** Stimulation is whole-FOV only (`StimWholeFOV`), through a fluorescence preset such as `GFP` for blue light.
- **One LED for all fluorescence presets.** The X-Cite XT600 (`LED1 Device`) is the shutter of every fluorescence preset. `Ti2E` maps them all to its intensity property, so a `PowerChannel(config=..., power=...)` sets the LED in percent. DIC and QPI use the DiaLamp and take no power.
- **Hardware trigger config is not ready.** `NikonTi2e_hwtrigger.cfg` (camera output trigger drives the XT600) still has open problems; see the notes at the top of that file. Use `NikonTi2e.cfg`.
- **Preset mapping from the Pertzlab scopes:** `miRFP` is `iRFP`, `mScarlet3` is `RFP`, `CyanStim` is `GFP`, `mCitrine` is `YFP_Custom`.
