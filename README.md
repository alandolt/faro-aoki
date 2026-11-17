# faro-aoki

Aoki lab microscopes for [faro](https://github.com/pertzlab/faro).

| Name | Class | Hardware | Config |
|------|-------|----------|--------|
| `ix83_unit2` | `faro_aoki.ix83_unit2.IX83Unit2` | Olympus IX83 (unit no. 2), Lumencor Spectra X, Teledyne Photometrics Prime Sigma (PVCAM) | `IX83Lumencor2.cfg` |
| `ti2e` | `faro_aoki.ti2e.Ti2E` | Nikon Ti2-E, X-Cite XT600, Hamamatsu DCAM camera; no DMD | `NikonTi2e.cfg` |

The Micro-Manager configs ship inside the package
([`src/faro_aoki/configs/`](src/faro_aoki/configs/)), so a class finds its
config on every PC. Micro-Manager itself is expected at
`C:\Program Files\Micro-Manager-2.0`.

## Use in an experiment

Depend on `faro-aoki`; it brings faro along:

```toml
[project]
dependencies = ["faro-aoki"]

[tool.uv.sources]
faro-aoki = { git = "https://github.com/alandolt/faro-aoki.git", branch = "main" }
```

```python
from faro_aoki.ix83_unit2 import IX83Unit2

mic = IX83Unit2()
```

The GUI finds the scopes by name:

```bash
uv run faro-napari ix83_unit2
uv run faro-napari ti2e
```

Use `faro-napari` rather than plain napari-micromanager for the IX83: the
PVCAM adapter hands out each snapped frame only once, and `faro-napari`
installs faro's snap cache so the Snap button works.

### Editable checkouts of faro and faro-aoki

To read and change the code that runs, clone the repositories next to each
other and install both as editable:

```
code/
  faro/
  faro-aoki/
  faro-experiments/<experiment>/
```

```toml
[tool.uv]
# faro-aoki pins faro to git main; this replaces that pin with the clone.
# It replaces every faro requirement, so list the faro extras you need here,
# e.g. ["faro[cellpose]"].
override-dependencies = ["faro"]

[tool.uv.sources]
faro      = { path = "../../faro",      editable = true }
faro-aoki = { path = "../../faro-aoki", editable = true }
```

Without the override, uv stops with "conflicting URLs for package `faro`".
With `override-dependencies = ["faro"]`, faro extras given in `dependencies`
(e.g. `faro[cellpose]`) are dropped silently, so put them in the override.
The same holds for any faro source other than git main, e.g. a `rev` pin.
After adding or renaming a scope in `pyproject.toml`, run `uv sync` (a running
Jupyter kernel needs a restart) so the new name is registered.

## Examples

[`examples/ti2e/`](examples/ti2e/) has the faro example experiments adapted
to the Ti2-E.

## IX83 config

The `Channel`, `Objective`, `Binning` and `System` presets of
`IX83Lumencor2.cfg` are generated from MetaMorph's illumination settings.
Change the script, not the generated block, then rerun it:

```bash
uv run python tools/ix83_unit2/ils_to_mm_presets.py tools/ix83_unit2/illuminationsettings.ILS src/faro_aoki/configs/IX83Lumencor2.cfg
```

Every preset of a config group must set the same (device, property) set:
pymmcore-widgets keeps only the properties of a group's first preset and drops
the rest. `tests/test_package.py` checks this for both configs.

## Development

```bash
git clone https://github.com/alandolt/faro-aoki.git
cd faro-aoki
uv sync                      # with pytest and pre-commit (dev group)
uv run pytest
```

To work on faro at the same time, switch the faro source in `pyproject.toml` to
the commented `path = "../faro"` line.

Hardware tests go to `tests/hardware/`. `faro.testing.plugin` (loaded in
`tests/conftest.py`) gives them `--scope <name>` and the generic fixtures;
without `--scope` they are skipped.

## License

MIT, see `LICENSE`.
