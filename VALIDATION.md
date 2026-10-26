# Validation record

## Network scenarios and plot options, 2026-10-26

**124 tests passed:** the full 122-test suite passed in 122.16 seconds, followed
by two additional preset-source checks. A final targeted rerun also verifies
that mean mode restores the previous HSI/WUA selection when switched off.
The suite covers independent network regressions, physical-cache reuse across
life stages, map isolation from all four local overrides, per-COMID persistence,
D84 resistance and substrate effects, missing-geometry recovery, full-flow mean
integration and sampling convergence, matching map/legend temperature stops,
new labels, collapsed above-bankfull diagnostics, the curve dialog, and the
exact modeled cross-section grid. The original frozen-R checks still pass.

The original GIFT model files, input GeoPackages, and prepared CHaMP data are
byte-for-byte unchanged. No dependencies or online calls were added to the app.

A fresh local AppTest process initialized in **3.311 seconds including imports**;
app execution took 2.014 seconds and performed **zero hydraulic solves**. A
cached rerun took 0.188 seconds. One alternative geometry (Bieger 2015 National
width / Regional depth) solved all 728 reaches in 3.594 seconds; its first
201-sample full-flow summary took 20.427 seconds. The latter tasks run only
when requested and are cached independently of the selected month period.
These are local backend timings, not deployment, browser, or concurrency tests.

**Outstanding source data:** the named GIFT Shiny Default preset loader is
implemented, but no raw live-Shiny default curves could be verified. The live
curves differ from the published R-guide Ptolemy example. This preset remains
explicitly unavailable until verified source CSVs are supplied; no different
curves were relabeled as Shiny defaults. See
`inputs/curves/SHINY_DEFAULT_SOURCE.md`. All other curve options are operational.

## Selected-segment hydraulic options, 2026-10-25

`python -m pytest -q` passed **96 tests** in the updated app package. The 14 new
checks cover published regression estimates and USGS unit conventions,
independent width/depth choices, omission of the maximum-depth argument for all
alternative/custom geometry, slope-only scaling, invalid shape recovery,
scenario metadata in CSV exports, cache reuse, network-score isolation,
per-segment custom-value persistence, reset, and plotting when the original
CHaMP dimensions are missing.

The existing 82 scientific, input-preparation, portability, on-demand, and app
state checks also pass. The original GIFT hydraulic equations, input data, and
prepared network scores are unchanged. Castro and Jackson coefficients were
verified against the USGS NSS Western Cordillera response stored under
`tests/regression_reference/`. Tests used the pinned application dependencies
and Streamlit's official AppTest runner; browser rendering was not separately
tested. No deployment was performed.

Updated 2026-10-23. Run `run_checks.py` directly in VSCode to repeat the suite.
Install `pytest` for development checks; normal app use does not require it.

## Current input verification

- All 728 prepared reaches match bankfull width, mean depth, and maximum depth
  in the configured `UGR_channel_geometry_predictions_monthly_EROM.gpkg`.
- Temperature (`currTempScoreKSee`), priority (`High priority combined`), and
  category (`FinalScore_cat`) come from the supplied Provisional Model Layer
  GeoPackage, copied unchanged to `inputs/Provisional_Model_Layer.gpkg`.
  Its `provisional_model_layer` layer has 728 unique COMIDs. All stream COMIDs match, with no null
  temperature or priority scores.
- Pyles Creek, COMID 23429054: bankfull width is 4.911802553596989 m and mean
  bankfull depth is 0.24333286885422614 m. The previous prepared files held
  4.534552403349192 m and 0.258162206878533 m, respectively.
- The monthly overview contains all 727 supported reaches. Selected native
  hydraulics are calculated on demand; native `.bin` files are not required.
  COMID 23429096 remains unavailable because its bankfull geometry is missing.
- July-September rearing coverage is 696/728 complete reaches. March-June
  steelhead-spawning coverage is 407/728. Current geometry produces 166 shape
  factors above 0.7; all are retained without capping.

## Automated checks

The suite verifies numerical agreement with the original R GIFT calculations,
source joins, configurable fields and units, rebuild behavior, exports, and
Streamlit controls. **82 tests passed** through `python run_checks.py` in the
extracted release package, with no native hydraulic files present: two overview
portability tests ran first, followed by 80 remaining tests.

The frozen R references use revision
`40c4a74f82d842cd2ab8ab4c53e2b985ac4e0030`, R 4.2.2, dplyr 1.0.10,
zoo 1.8-11, and birk 2.1.2. The R source, inputs, generator, provenance, and
hashes remain in `tests/r_reference` and were not regenerated in this revision.

- 19 hydraulic cases include shape factors above 0.7 and 11 historical reaches.
  Numerical tolerances are relative 2e-9 and absolute 2e-11.
- 1,728 habitat evaluations cover six curve sets and three substrate treatments.
  Given identical hydraulics, absolute tolerance is 2e-12.
- 792 monthly evaluations and selected-period medians use their frozen
  hydraulic inputs. These references are independent of later changes to the
  application's input GeoPackage.
- Data-preparation tests use separate source files with the same basename,
  custom layers and join keys, alternate width columns, feet, percent slope,
  D84 in meters, and monthly flows in cfs.
- Source path/content, layer, field, units, curve, and period changes trigger
  complete rebuilds in the explicit offline preparation tool. The interactive
  app refreshes inputs without solving network hydraulics; changed reaches are
  calculated on selection. Missing/corrupt native files do not affect startup.
- Missing paths, misspelled columns, and duplicate join IDs raise errors.
  Failed offline preparation preserves the previous complete files. An invalid
  live configuration stops the app instead of showing stale source values.
- AppTest verifies life-stage/month controls, selections in all four comparison
  plots, map/inspector synchronization, missing-input diagnostics, cache reuse,
  lazy plot rendering, and reloading a changed width mapping.
- On-demand checks assert zero startup hydraulic solves, one solve for each new
  selected reach, and reuse across repeat selections, life stages, months, and
  units. Startup is also checked with missing/corrupt overview files and without
  native files. Changed-source results update the map on selection. Separate
  AppTest sessions retain their own evaluated-reach comparisons.

Browser rendering, external basemap availability, deployment, and concurrent
users were not independently tested for this revision. Historical timings in
README.md do not describe a new performance measurement.

## Deployment fixes

- Text-file LF line endings are enforced by `.gitattributes`; the normalized
  model sources and prepared monthly overview are included in the update.
- Direct application dependencies are pinned to the tested versions below.
  Local Conda setup is in `dev/environment.yml`; Cloud uses `requirements.txt`.
- `run_checks.py` tests overview validity without native files before app tests.
- Docker startup uses the host's `PORT`, with 8501 as the default.
- The GIFT model equations are unchanged. Selected hydraulic curves and monthly
  interpolation use the existing implementation and scientific tolerances.
- The Docker image was not built, and local Conda creation was not tested here.

## Local startup measurement

With dependencies already installed, a fresh Python process initialized the
AppTest backend in 2.068 seconds, including imports. The app script itself took
1.382 seconds and performed zero hydraulic solves. Selecting two different
reaches took 0.310 and 0.302 seconds per backend update and performed one solve
for each. Returning to the first reach took 0.231 seconds without another solve;
changing the life stage also reused the cached physical solution.

These local measurements exclude browser rendering, hosting builds, internet
latency, and concurrent users. They are not a hosted startup-time guarantee.

## Tested Python versions

| Component | Version |
| --- | --- |
| Python | 3.12 |
| Streamlit | 1.66.1 |
| NumPy | 2.3.5 |
| pandas | 2.2.3 |
| Plotly | 6.9.0 |
| PyDeck | 0.9.3 |
| Shapely | 2.2.0 |
| pyproj | 3.8.0 |
| pytest | 9.1.1 |
