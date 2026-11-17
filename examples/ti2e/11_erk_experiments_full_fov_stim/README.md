# ERK-KTR whole-FOV stimulation on the Ti2-E

Adapted from the Pertzlab Jungfrau experiments. The Ti2-E has no DMD, so the
stimulation always lights the whole field of view (`StimWholeFOV`).

## Channels

| Role | Jungfrau preset | Ti2-E preset |
|------|-----------------|--------------|
| Nuclear marker (H2B-miRFP), segmented | `miRFP` | `iRFP` |
| ERK-KTR reporter (mScarlet3) | `mScarlet3` | `RFP` |
| Stimulation, blue light | `CyanStim` | `GFP` |
| Optocheck (mCitrine) | `mCitrine` | `YFP_Custom` |

All presets share the X-Cite XT600 LED. The `power` of a `PowerChannel` sets the
LED intensity in percent. Exposures and powers in the notebooks are the Jungfrau
values; tune them for the XT600.

Segmentation uses Cellpose v4: `uv sync --extra cellpose`. Each notebook names
`OtsuSegmentator` as the alternative without Cellpose.

## Notebooks

### `stim_rtmsequence.ipynb`: RTMSequence API (recommended)

A multi-phase experiment declared with `RTMSequence` objects (time plan,
channels, stim frames, ref frames) and joined with `combine`.

### `stim_dfacquire.ipynb`: df_acquire API

The same kind of experiment with the legacy `df_acquire` DataFrame API:
`generate_df_acquire()` and `apply_stim_treatments_to_df_acquire()`, converted
with `df_to_events()`. The second phase runs with `continue_experiment()` on the
same controller.

### `stim_ramp_dfacquire.ipynb`: drug test with pre-exposure (df_acquire API)

Three FOV groups with different treatments, each split into a pre-drug and a
post-drug half, with manual pipetting in between. Shows `StimTreatment` with
ramped exposures and `continue_experiment()` across phases.

Every notebook has a `WRITER` setting: `"omezarr"` (one OME-Zarr store) or
`"tiff"` (one TIFF per frame). The ramp notebook defaults to `"tiff"`: its FOV
groups 2 and 3 join the run later, and the `OmeZarrWriter` of this faro version
cannot add FOVs to a running store (fixed on the branch
`fix/omezarr-grow-positions`, not merged yet).
