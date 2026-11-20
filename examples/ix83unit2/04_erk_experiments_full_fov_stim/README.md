# ERK-KTR whole-FOV stimulation on the IX83 unit 2

Adapted from the Pertzlab Jungfrau experiments. The IX83 unit 2 has no DMD, so
the stimulation always lights the whole field of view (`StimWholeFOV`).

## Channels

| Role | Jungfrau preset | IX83 unit 2 preset | Spectra LED |
|------|-----------------|--------------------|-------------|
| Nuclear marker (H2B-miRFP), segmented | `miRFP` | `iRFP` | red |
| ERK-KTR reporter (mScarlet3) | `mScarlet3` | `RFP` | green |
| Stimulation, blue light | `CyanStim` | `GFP` | cyan |
| Optocheck (mCitrine) | `mCitrine` | `YFP` | green |

Each preset turns on one LED of the Lumencor Spectra X. The `power` of a
`PowerChannel` sets the level of that LED (0-99). Exposures and powers in the
notebook are the Jungfrau values; tune them for the Spectra.

Segmentation uses Cellpose v4: `uv sync --group cellpose`. The notebook names
`OtsuSegmentator` as the alternative without Cellpose.

## Notebook

### `stim_rtmsequence.ipynb`

A multi-phase experiment declared with `RTMSequence` objects (time plan,
channels, stim frames, ref frames) and joined with `combine`. The `WRITER`
setting picks `"omezarr"` (one OME-Zarr store) or `"tiff"` (one TIFF per
frame).

## GPU

Cellpose (and convpaint) run on the GPU only if torch sees CUDA:

```bash
uv run python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

The lock installs the CUDA 13.0 build of torch (`+cu130`), which needs an
NVIDIA driver >= 580.65 (`nvidia-smi` shows the version). With an older driver
`is_available()` is `False` and both fall back to the CPU without an error.
Cellpose-SAM on the CPU is very slow and needs a lot of memory on a full camera
frame; the kernel can die without a message.
