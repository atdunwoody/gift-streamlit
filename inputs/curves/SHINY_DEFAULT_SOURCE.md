# GIFT Shiny Default preset: source values still required

The app includes a named **GIFT Shiny Default** preset loader. The preset is
unavailable in this release because its original CSV values could not be verified.
No Ptolemy or synthetic curves have been substituted.

The live author's app at https://sgronsdahl.shinyapps.io/GIFT/ was inspected on
2026-10-26. It provides default depth, velocity, and substrate plots, but no
raw-curve download or public server source was found. Those plotted defaults
differ from the Ptolemy rainbow-trout parr example published with the R guide.
The R guide at revision `40c4a74f82d842cd2ab8ab4c53e2b985ac4e0030` uses that
Ptolemy example; it is not evidence that the live Shiny app uses the same curves.

To enable the preset, place verified source files here:

| Filename | Columns | Units |
| --- | --- | --- |
| gift_shiny_default_depth.csv | depth, suit | m, 0 to 1 |
| gift_shiny_default_velocity.csv | velocity, suit | m/s, 0 to 1 |
| gift_shiny_default_substrate.csv | lower, upper, suit | mm, mm, 0 to 1 |

Record the original source, version/date, and any conversions in this document.
The app validates file structure and numeric ranges; it cannot independently
authenticate a user's file provenance. Restart or rerun the app after adding
the files. The preset appears in the suitability selector under its requested
name and uses these three CSVs directly.

The other species/life-stage and custom-upload curve options remain available.
