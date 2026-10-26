# Selected-segment hydraulic options

Select a segment, then open **Habitat response to flow > Adjust selected-segment
hydraulics**. Width and mean depth have independent source selectors:

- CHaMP Regression: the existing configured input values, selected by default.
- Bieger National: the nationwide relationship in Bieger et al. (2015), Table 3.
- Bieger Regional: the division-level relationship selected by `BIEGER_REGION`
  in `settings.py`. The supplied network uses `IMP`, Intermontane Plateau.
- Castro and Jackson 2001: the Western Cordillera relationship, including the
  Blue Mountains, with coefficients and units verified against USGS StreamStats.
- Custom value: enter a positive width or mean depth in metres.

**Slope for plotting (m/m)** can be edited independently. The default is the
selected segment's configured source slope. ft/ft has the same numeric value.
Controls update the active plot and the segment's monthly plot table. A reset
button restores both CHaMP sources and the segment's original slope.

## Equations

| Source | Bankfull width | Mean bankfull depth | Input/output units |
| --- | --- | --- | --- |
| Bieger National | `2.70 * DA**0.352` | `0.30 * DA**0.213` | DA in km2; geometry in m |
| Bieger Regional, IMP | `1.11 * DA**0.415` | `0.07 * DA**0.329` | DA in km2; geometry in m |
| Castro and Jackson, Western Cordillera | `9.40 * DA**0.42` | `0.61 * DA**0.33` | DA in mi2; geometry in ft, then converted to m |

Bieger coefficients retain the printed precision in Table 3. Regional ranges
are those tabulated in Bieger Table 2. Other Bieger division coefficients are
included in `bankfull_regressions.py` for networks using a different division.

The Castro and Jackson option uses USGS NSS regression region **847**, code
**GC1857**, `Western_Cordillera_CastroJackson_2001`. Its stated drainage-area
range is 19.6-5,090 mi2. At 100 mi2, the USGS estimate returns 65.0 ft width and
2.79 ft mean depth. The returned equations, units, and estimates are retained
in `tests/regression_reference/castro_jackson_usgs.json` as an offline check.
The app displays a note when a selected equation is used outside its stated
drainage-area range. No online service is called by the app.

## Maximum depth and shape

When both geometry sources are CHaMP Regression, the existing maximum bankfull
depth is supplied. A slope-only adjustment also retains this original geometry.

Selecting an alternative regression or custom value for either width or depth
omits the maximum-depth argument entirely. The original GIFT fallback computes:

```python
shape_factor = (bankfull_width / mean_bankfull_depth) / 100
```

The original maximum depth is not scaled or reused with alternative geometry.
GIFT's inferred maximum depth follows its own shape calculation. Shape factors
are not capped; inputs that imply a factor of 1 or greater are rejected with
an actionable message. A positive width and mean depth are required.

This maximum-depth policy differs from the earlier standalone sensitivity
analysis, which preserved shape by scaling mean and maximum depths together.
The selected-segment options now follow the requested no-maximum-depth policy.

## Scope, persistence, and downloads

- Adjustments apply to the selected segment's flow-response curves, gold
  monthly markers, monthly plot table, and segment-specific CSV downloads.
- The map, right-hand inspector, network comparison scatterplots, and network
  summary export retain their CHaMP Regression calculations.
- Choices are remembered independently for each segment in the current session.
  Returning to a segment restores its custom values and source choices.
  A changed input-data signature clears saved plot choices.
- Monthly and full-curve CSVs record the active width/depth sources, dimensions,
  slope, shape factor, and regression-region labels. Maximum depth is blank
  when the parameter is omitted. Flow units for downloads remain SI.
- Curves use the existing bounded hydraulic and habitat caches. Changing inputs
  solves only the selected segment. Restart and deployment require no additional
  Python dependencies or network services.

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
