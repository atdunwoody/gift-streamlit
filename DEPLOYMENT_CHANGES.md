# Apply the deployment changes

This archive contains new or changed files relative to gift-streamlit(1).zip.
It is an update for the existing repository, not a standalone application.

1. Stop the local Streamlit server.
2. Extract this archive into the repository folder containing `app.py`, retaining
   its folder structure. Merge the folders and overwrite matching files when
   prompted, including those in `data/` and `model/`. Keep existing files that
   are absent from this archive.
3. **Delete the old `environment.yml` from the repository root.** Its replacement
   is `dev/environment.yml`. ZIP extraction cannot remove the old file for you.
4. In the Python 3.12 environment used by VSCode, run
   `python -m pip install -r requirements.txt`.
5. For verification, install `pytest` if needed, then open `run_checks.py` in
   VSCode and choose **Run Python File in Terminal**. Check before starting the
   app so an automatic rebuild cannot conceal a stale prepared-data manifest.
6. Commit and push all changed and new files, including the root-file deletion,
   `.gitattributes`, normalized model source files, and prepared data. Inspect the
   changes in GitHub Desktop before committing.
7. In Streamlit Community Cloud, deploy `app.py` and select Python 3.12 in
   Advanced settings. The root `requirements.txt` supplies the pinned packages.

For a new local environment, run `conda env create -f dev/environment.yml`, then
activate `gift_streamlit`. To launch locally, run `run_streamlit.py` in VSCode.

## Included fixes

- LF line endings for text assets on Windows and Linux, with binary protection
  for GeoPackages and native hydraulics.
- Prepared data regenerated against the normalized source files.
- Pinned versions of the seven direct application dependencies.
- Local Conda configuration moved into `dev/`, leaving `requirements.txt` as the
  root deployment dependency file.
- Docker startup honors the host's `PORT`, defaulting to 8501.
- `run_checks.py` tests the prepared-data manifest before starting app tests.
- Updated installation, deployment, and verification instructions.

The changed prepared files include numerical differences from regenerating on
Linux. The scientific reference suite checks their agreement within its existing
tolerances. Input data and model equations were not changed by this update.

The Docker image was not built here. Live hosting, browser rendering, and
concurrent-user behavior require verification on the selected host.
