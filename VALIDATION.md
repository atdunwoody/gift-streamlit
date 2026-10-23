# Validation record

Verified 2026-10-22. Run `run_checks.py` directly in VSCode to repeat the suite.
Install `pytest` for development checks; normal app use does not require it.

## Current input verification

- All 728 prepared reaches match bankfull width, mean depth, and maximum depth
  in the configured `UGR_channel_geometry_predictions_monthly_EROM.gpkg`.
- Temperature (`currTempScoreKSee`), priority (`High priority combined`), and
  category (`FinalScore_cat`) come from the supplied Provisional Model Layer
  GeoPackage, copied unchanged to `inputs/Provisional_Model_Layer.gpkg`.
  Its `UGR` layer has 728 unique COMIDs. All stream COMIDs match, with no null
  temperature or priority scores.
- Pyles Creek, COMID 23429054: bankfull width is 4.911802553596989 m and mean
  bankfull depth is 0.24333286885422614 m. The previous prepared files held
  4.534552403349192 m and 0.258162206878533 m, respectively.
- Prepared native hydraulics were rebuilt for all 727 supported reaches.
  COMID 23429096 remains unavailable because its bankfull geometry is missing.
- July-September rearing coverage is 696/728 complete reaches. March-June
  steelhead-spawning coverage is 407/728. Current geometry produces 166 shape
  factors above 0.7; all are retained without capping.

## Automated checks

The suite verifies numerical agreement with the original R GIFT calculations,
source joins, configurable fields and units, rebuild behavior, exports, and
Streamlit controls. **75 tests passed** using `python run_checks.py`: two
prepared-data portability tests ran first, followed by 73 remaining tests.

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
  complete rebuilds. Unchanged inputs reuse prepared data. Missing/corrupt
  native curves are rebuilt; removed reaches leave no obsolete native file.
- Missing paths, misspelled columns, and duplicate join IDs raise errors.
  Failed preparation preserves the previous complete files, while the app
  stops and does not render them as current data.
- AppTest verifies life-stage/month controls, selections in all four comparison
  plots, map/inspector synchronization, missing-input diagnostics, cache reuse,
  lazy plot rendering, and reloading a changed width mapping.

Browser rendering, external basemap availability, deployment, and concurrent
users were not independently tested for this revision. Historical timings in
README.md do not describe a new performance measurement.

## Deployment fixes

- Text-file LF line endings are enforced by `.gitattributes`; the normalized
  model sources and regenerated prepared outputs are included in the update.
- Direct application dependencies are pinned to the tested versions below.
  Local Conda setup is in `dev/environment.yml`; Cloud uses `requirements.txt`.
- `run_checks.py` tests bundled-data validity before app tests can rebuild it.
- Docker startup uses the host's `PORT`, with 8501 as the default.
- On the Linux verification host, fresh Git clones with `core.autocrlf=false`
  and `core.autocrlf=true` both passed the two portability tests without a
  rebuild. This checks Git conversion behavior; it is not a Windows OS test.
- Model source changes are limited to line endings. Scientific reference tests
  passed for the regenerated Linux outputs within the existing tolerances.
- The Docker image was not built, and local Conda creation was not tested here.

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
