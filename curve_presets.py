"""Load the GIFT Shiny default preset from its explicitly identified CSV files."""
from pathlib import Path

from habitat_engine import curve_from_csvs

ROOT = Path(__file__).resolve().parent
SHINY_ID = "gift_shiny_default"


def gift_shiny_default():
    metadata = dict(id=SHINY_ID, label="GIFT Shiny Default", defaultStart=6, defaultEnd=8,
                    defaultMonth=7, defaultMode="range",
                    periodNote="Editable late-summer assessment period for the default-curve comparison.",
                    periodSource="")
    paths = [ROOT / "inputs" / "curves" / f"gift_shiny_default_{kind}.csv"
             for kind in ("depth", "velocity", "substrate")]
    if not all(path.is_file() for path in paths):
        return dict(metadata, available=False,
                    curveNote="The live Shiny defaults differ from the published R-guide example. "
                              "Their original CSV values have not been verified; no substitute curves are used.")
    try:
        curve = curve_from_csvs(*(path.read_bytes() for path in paths), label=metadata["label"])
    except (ValueError, OSError) as exc:
        return dict(metadata, available=False, curveNote=f"The Shiny default CSV preset is invalid: {exc}")
    return dict(curve, **metadata, available=True,
                curveNote="Shiny default CSV preset loaded from inputs/curves. "
                          "See SHINY_DEFAULT_SOURCE.md for provenance requirements.")
