# On-demand hydraulic curves

This is the complete updated application, including the earlier deployment fixes.
The input data and monthly map overview are included. Detailed curves are
calculated for the selected segment and cached in the running server.

## Install or update

1. Extract the complete `gift-streamlit` folder and open it in VSCode.
2. When copying into an existing repository, overwrite matching application
   files and remove the old root `environment.yml`. The local Conda file is now
   `dev/environment.yml`. The old `data/hydraulics/` folder can also be removed;
   the webapp does not read or validate those native files.
3. In the existing Python 3.12 environment, install `requirements.txt`, then
   launch `run_streamlit.py` directly in VSCode. For a new environment, run
   `conda env create -f dev/environment.yml` and activate `gift_streamlit`.
4. Commit and push the updated source, overview files, and any legacy-file
   deletions. In Streamlit Community Cloud, use `app.py` as the entrypoint and
   Python 3.12 in Advanced settings.

No preparation run is needed for the supplied inputs. `prepare_data.py` remains
an explicit offline option to refresh the complete monthly overview after input
changes. Running it also produces optional native files that the webapp ignores.

## Startup and selection behavior

- Startup performs zero hydraulic curve solves and does not select a segment.
- The map retains the prepared monthly overview for matching source inputs.
- Clicking a segment or comparison point calculates that segment's hydraulic
  curve and evaluates its monthly habitat results and flow-response plots.
- Repeat clicks reuse cached hydraulics. Changing the life stage, months, or
  display units also reuses the physical solution.
- Physical cache entries are keyed by segment, hydraulic inputs, and calculation
  code. The physical cache holds at most 256 entries; habitat caches are also
  bounded. Server restarts clear these caches, and old entries can be evicted.
- Changed inputs are read without a network hydraulic rebuild. Reaches without
  matching overview values are gray until selected. Their calculated results
  update the map, comparisons, and network export for that user's session.
- Missing or corrupt overview files also leave hydraulics deferred to selection.
  Invalid source paths, layers, or required fields produce an input error.
- The original GIFT equations, uncapped shape factor, flow-range rules, and
  scientific reference tolerances are retained.

## Check the update

Install `pytest` for development checks, then run `run_checks.py` in VSCode.
The suite verifies zero startup solves, one solve for each newly selected reach,
cache reuse, changed inputs, overview updates, missing native files, and R-derived
scientific references. `VALIDATION.md` records the completed verification.

The first hosting build can still spend time installing Python dependencies.
This change removes bulk hydraulic work from application startup; it does not
control the hosting platform's build queue, package downloads, or instance startup.
The Docker image and concurrent browser users were not tested here.
