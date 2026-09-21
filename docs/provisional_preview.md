# Provisional schedule preview

This workflow renders an explicitly invalid schedule snapshot for investigation without weakening the normal candidate-publication gate. It is intended for a private Codespaces port, never GitHub Pages.

```bash
python -m pip install -e .
python -m caa_scheduler build-candidate \
  builds/schedule_7_v0_2_0/build_config.json \
  --provisional-preview
python -m caa_scheduler build-web \
  --manifest web/schedules.preview.json \
  --output dist-preview
python -m http.server --directory dist-preview 8000
```

In Codespaces, open port 8000 and keep its visibility **Private**. The preview manifest makes the provisional schedule the only selection and displays a persistent red warning.

When using the prepared sandbox-preview ZIP, extract it in Codespaces and run only:

```bash
python -m http.server --directory dist-preview 8000
```

The included Git bundle contains the implementation commits for later branch synchronization; it is not required to view the prebuilt site.

`--provisional-preview` is opt-in. It allows a fully materialized but infeasible exact incumbent to receive temporary canonical identifiers and consumer exports. The build report remains non-publishable, retains its blockers and hard stops, and marks the package `previewOnly`. A normal build continues to suppress these files.

The preview build directory is ignored by Git. Do not copy its outputs into `data/schedules`, add them to `web/schedules.json`, deploy them through the Pages workflow, or treat them as a Schedule 7 release package.
