# Design QA

Source visual: `C:/Users/ynyyzyrf/AppData/Local/Temp/codex-clipboard-902a55dd-deb6-439d-a197-1f4c61a1254c.png`

Implementation scope:
- Reworked the mini program visual language toward the reference: blue brand system, white rounded cards, soft shadows, campus imagery, feature grid, activity cards, directory cards, news cards, profile menu, and form/detail page color alignment.
- Added local image asset `miniprogram/assets/campus-hero.png`.

Verification:
- `npx tsc --noEmit --pretty false`: passed.
- Legacy green/emoji scan for core mini program styles: passed, only `--ink: #111827` remains as a text color.
- WeChat DevTools CLI `build-npm`: blocked because IDE Service Port is disabled in WeChat DevTools security settings.

Visual comparison:
- Reference image was inspected.
- Rendered mini program screenshot could not be captured in this environment because the WeChat DevTools service port is disabled.

Final result: blocked

Blocker to resolve:
- Open WeChat DevTools -> Settings -> Security Settings -> enable Service Port, then rerun `D:\微信開發者工具\微信web开发者工具\cli.bat build-npm --project D:\wxapp\campus_platform` and capture the mini program pages for visual comparison.
