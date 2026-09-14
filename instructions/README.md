# Build-instruction sources

`CAA_Build_Instructions_TEMPLATE_v2_0.md` is the primary instruction document carried forward from the Claude-era project. Files under `additions/` are approved instruction additions that have not yet been folded into a newly versioned primary document.

These Markdown files are authoritative. The browser-facing instruction catalog is generated from them by `python -m caa_scheduler build-web`; do not hand-edit the generated JSON in `dist/`.

For the current read-only console, instruction changes follow the normal repository workflow:

1. Edit the relevant Markdown source.
2. Update the instruction version in `web/schedules.json` when the change constitutes a new document version.
3. Run the Python and JavaScript test suites and rebuild the web console.
4. Review and merge the change through a pull request.

A future in-app editor should update these same Markdown sources through the secure publish service, preserving one instruction source of truth.
