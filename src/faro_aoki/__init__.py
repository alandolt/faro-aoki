"""Aoki lab microscopes for faro: Olympus IX83 unit 2 and Nikon Ti2-E."""

import useq

# Extra plate formats for the plate widgets and the stage map. Every faro_aoki
# scope imports this package first, so the plates are registered before the
# widgets are built.
useq.register_well_plates(
    {
        # Matsunami glass bottom dish: 35 mm dish, 14 mm glass. The glass area
        # is the single round well.
        "matsunami-35mm-dish-14mm-glass": {
            "rows": 1,
            "columns": 1,
            "well_spacing": 0.0,
            "well_size": 14.0,
            "circular_wells": True,
            "name": "Matsunami 35 mm dish, 14 mm glass",
        },
    }
)
