# Network and selected-segment hydraulic options

Use **Network bankfull geometry** in the sidebar to choose independent width
and mean-depth regressions for every segment. The default is CHaMP Regression
for both dimensions. The map, inspector, comparison plots, and network export
use these network choices. Bieger options are labeled **Bieger 2015 National**
and **Bieger 2015 Regional**.

## Segment-only overrides

Select a segment, then open **Adjust selected-segment hydraulics**. Independent
on/off switches allow custom bankfull width (m), mean bankfull depth (m), slope
(m/m), and D84 (mm). Unchecked fields follow the current network scenario.
Custom values update only the response curves, Channel Geometry tab, monthly
plot table, and segment CSV downloads. The map and network comparisons retain
the sidebar regressions. D84 affects both hydraulic resistance and the substrate
suitability class; it is one representative grain size, not a grain-size distribution.

Overrides persist by COMID in the current session, including when network
regressions or species change. **Reset plot inputs** restores the active network
scenario for that segment. Changing the underlying source data clears overrides.
Invalid geometry remains unavailable with an explanation and can be corrected
through the custom inputs; the app does not reuse the old scenario's scores.

## Equations

| Source | Bankfull width | Mean bankfull depth | Input/output units |
| --- | --- | --- | --- |
| Bieger 2015 National | `2.70 * DA**0.352` | `0.30 * DA**0.213` | DA in km2; geometry in m |
| Bieger 2015 Regional, IMP | `1.11 * DA**0.415` | `0.07 * DA**0.329` | DA in km2; geometry in m |
| Castro and Jackson 2001, Western Cordillera | `9.40 * DA**0.42` | `0.61 * DA**0.33` | DA in mi2; geometry in ft, converted to m |

Bieger uses the printed Table 3 coefficients. `BIEGER_REGION` in `settings.py`
selects the division for the Regional option; the supplied basin uses `IMP`,
Intermontane Plateau. All eight divisions and their Table 2 drainage-area ranges
are included. Domain-extrapolation notes appear with the selected segment.
Castro and Jackson uses USGS NSS region 847 (GC1857), Western Cordillera;
its published drainage-area range is 19.6 to 5,090 mi2. The official response
at 100 mi2 returns 65.0 ft width and 2.79 ft depth and is retained under
`tests/regression_reference/`. The running app calls no online regression service.

## Maximum depth and the Channel Geometry tab

When both network geometry sources are CHaMP, the source maximum bankfull depth
is used. Slope-only or D84-only overrides preserve it. Any alternative regression
or custom width/depth omits the maximum-depth argument entirely. The original
GIFT fallback is `shape_factor = (bankfull_width / mean_bankfull_depth) / 100`.
Factors are not capped; values outside [0, 1) are unavailable.

The **Channel Geometry** tab plots the exact 10,001-point cross-section grid used
by the hydraulic simulator, with the bankfull water surface at elevation zero.
It follows the active segment plot inputs. Axes use metres; vertical exaggeration
is stated. This is GIFT's assumed section, not a surveyed section. Maximum depth
shown there is the model's resulting geometry and is not an added input or cap.

## Selected-flow map versus mean-HSI map

The mean-HSI switch defaults off. The default map is unchanged: habitat is
calculated at each exact monthly EROM flow, then the median of selected months
is mapped. Complete/partial-period rules still apply.

With the switch on, each segment's mean HSI over its full modeled flow curve is
mapped. This is a separate mean for each segment, not one basin-wide number.
The calculation uses 201 equally spaced discharges from the native modeled
minimum to bankfull, linearly interpolates hydraulic variables, evaluates the
existing GIFT habitat equations at each discharge, and divides the trapezoidal
integral of HSI by the modeled discharge range. It does not extrapolate to zero
or above bankfull. This is an average over discharge, not a time mean and not
weighted by flow duration. Mean component suitability is reported separately;
mean HSI is not obtained by multiplying mean components.

Mean mode drives the habitat map, HSI comparisons, and network summary export.
The inspector and gold response-plot markers continue to show selected monthly
flows. HSI is the map metric in mean mode; switching off restores the prior
HSI/WUA choice. Temperature and provisional priority values remain unchanged.

## Curve viewer and the Shiny preset

**View Suitability Curves** in the sidebar opens a dialog with the active depth,
velocity, and substrate curves. It works for the supplied life stages and custom
uploads. Substrate plots show each class interval explicitly.

The requested **GIFT Shiny Default** preset loader is present, but its raw source
values remain unverified and it is unavailable in this release. The live author's
Shiny defaults differ from the Ptolemy example in the public R guide. No curves
have been substituted. See `inputs/curves/SHINY_DEFAULT_SOURCE.md` for the exact
CSV filenames needed to enable it. All existing curve options remain available.

## Performance and exports

Default CHaMP startup still performs zero hydraulic solves and uses the bundled
monthly overview. Changing a network regression solves the network on demand.
Two complete physical scenarios are cached independently of suitability curves;
monthly and full-flow habitat summaries have their own bounded caches. Selecting
a segment and changing plot overrides use the existing per-segment caches.
No dependencies or online services were added.

Network exports record active width/depth sources and explicitly distinguish
selected-month medians from full-flow means. Full-flow coverage is counted in
flow samples; monthly coverage remains counted in months. Segment CSVs record
active sources, width, mean depth, slope, D84, shape factor, and optional maximum
depth. Original source GeoPackages and prepared CHaMP data are unchanged.

## References

Bieger K., Rathjens H., Allen P.M., and Arnold J.G. (2015). Development and
Evaluation of Bankfull Hydraulic Geometry Relationships for the Physiographic
Regions of the United States. JAWRA 51:842-858. Table 3.
https://doi.org/10.1111/jawr.12282

Castro J.M. and Jackson P.L. (2001). Bankfull Discharge Recurrence Intervals and
Regional Hydraulic Geometry Relationships: Patterns in the Pacific Northwest,
USA. JAWRA 37:1249-1262.
https://doi.org/10.1111/j.1752-1688.2001.tb03636.x

USGS NSS scenario definition:
https://streamstats.usgs.gov/nssservices/scenarios?regressionregions=847&statisticgroups=24

USGS estimates were obtained from the corresponding `scenarios/estimate`
service with drainage area set to 100 mi2 on 25 October 2026.
