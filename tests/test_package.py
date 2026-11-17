"""Checks of the package that need no hardware."""

from __future__ import annotations

from collections import defaultdict
from importlib.metadata import entry_points
from pathlib import Path

import pytest

from faro.microscope.pymmcore import (
    ConfigGroupControl,
    ContinuousFocusControl,
    DeviceControl,
)
from faro.microscope.registry import available_scopes, load_scope_class

SCOPES = {
    "ix83_unit2": "faro_aoki.ix83_unit2:IX83Unit2",
    "ti2e": "faro_aoki.ti2e:Ti2E",
}


def test_scopes_are_registered():
    registered = {ep.name: ep.value for ep in entry_points(group="faro.microscopes")}
    for name, target in SCOPES.items():
        assert registered.get(name) == target
        assert available_scopes()[name] == target


@pytest.mark.parametrize("name", sorted(SCOPES))
def test_config_ships_with_the_package(name):
    cls = load_scope_class(name)
    assert Path(cls.MICROMANAGER_CONFIG).is_file()


@pytest.mark.parametrize("name", sorted(SCOPES))
def test_presets_of_a_group_set_the_same_properties(name):
    """Every preset of a config group sets the same (device, property) set.

    pymmcore-widgets' PresetsWidget keeps only the properties of a group's
    first preset and deletes the others from the core's config, so a preset
    with extra properties silently does less in napari-micromanager.
    """
    cfg = Path(load_scope_class(name).MICROMANAGER_CONFIG)
    groups: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    for line in cfg.read_text(encoding="latin-1").splitlines():
        fields = line.split(",")
        if fields[0] != "ConfigGroup" or len(fields) < 6:
            continue
        _, group, preset, device, prop = fields[:5]
        groups[group][preset].add((device, prop))

    for group, presets in groups.items():
        first, *rest = sorted(presets)
        for preset in rest:
            assert presets[preset] == presets[first], (
                f"{cfg.name}: preset {group}/{preset} sets "
                f"{sorted(presets[preset] ^ presets[first])} differently "
                f"from {group}/{first}"
            )


@pytest.mark.parametrize("name", sorted(SCOPES))
def test_napari_controls_match_the_config(name):
    """Devices, groups and the autofocus of NAPARI_CONTROLS exist in the cfg.

    Property names come from the device adapters at runtime, so only the
    device of a property entry is checked here.
    """
    cls = load_scope_class(name)
    lines = [
        line.split(",")
        for line in Path(cls.MICROMANAGER_CONFIG)
        .read_text(encoding="latin-1")
        .splitlines()
    ]
    devices = {f[1] for f in lines if f[0] == "Device" and len(f) > 1}
    groups = {f[1] for f in lines if f[0] == "ConfigGroup" and len(f) > 1}
    autofocus = next(
        (f[3] for f in lines if f[:3] == ["Property", "Core", "AutoFocus"]), ""
    )

    for entry in cls.NAPARI_CONTROLS:
        if isinstance(entry, str):
            continue
        if isinstance(entry, ConfigGroupControl):
            assert entry.group in groups, entry
        elif isinstance(entry, ContinuousFocusControl):
            assert autofocus, f"{entry}: the cfg sets no autofocus device"
        elif isinstance(entry, DeviceControl):
            assert entry.device in devices, entry
        else:
            assert entry[0] in devices, entry
