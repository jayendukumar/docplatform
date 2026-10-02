# E1 dependency review

Date: 2026-09-22. This inventory was generated from pip dry-run resolution reports and the npm lockfile. **No licence exceptions have been approved yet.** Package metadata is evidence for review, not a complete legal or redistribution assessment.

See [machine-readable inventory](dependency-inventory.json), [DD-013/DD-022](design-decisions.md), [runtime lock](../backend/requirements.lock), [test lock](../backend/requirements-test.lock) and [npm lock](../frontend/package-lock.json).

## Exception scope needing resolution

- PostgreSQL runtime: PostgreSQL License, as explicitly required by E1-04.
- Python runtime and typing/greenlet components: PSF-2.0 and compound expressions.
- Reviewed BSD-2-Clause, BSD-3-Clause, ISC and MIT-0 foundation/build dependencies: not covered by the literal MIT/Apache/OFL list.
- certifi (MPL-2.0): test-only trust store pulled through HTTP test dependencies; it is not in the application runtime lock. Lightning CSS (MPL-2.0) is a Vite build dependency, including platform-specific optional binaries. Neither is a reason to assume approval for LibreOffice/MPL.
- Container base operating-system and browser-test binaries: broader transitive licences must be inventoried before distributing images. The application metadata list is not a complete container SBOM.
- Legacy/empty/compound metadata remains visible below and needs package LICENSE review; it is not silently normalized to an allowed licence.
- E2-04 adds `qrcode==8.2` (declared BSD) and `python-barcode==0.16.1` (declared MIT) for offline SVG generation. They are recorded as runtime dependencies, but the strict allow-list remains unresolved and no compliance claim is made.
- E2-15 adds `pypdf==6.1.3`; the wheel contains a BSD-style licence file, but it remains subject to the unresolved strict allow-list and full transitive/container review. It is used only for local PDF page compositing and does not fetch files or execute document content.
- E16 adds `pypdfium2==5.13.0` as **fidelity-harness tooling only** (DD-419): an optional `fidelity` extra and [`requirements-fidelity.lock`](../backend/requirements-fidelity.lock), never the runtime lock or application image. The bindings are `Apache-2.0 OR BSD-3-Clause`. The wheel bundles a PDFium binary whose reviewed component licences are PDFium BSD-3-Clause; pdfium-binaries MIT; abseil Apache-2.0; llvm-libc Apache-2.0 WITH LLVM-exception; FreeType FTL; ICU Unicode-3.0 (GPLv3 text only in an Autoconf-script exception); lcms2 MIT; libjpeg-turbo IJG/BSD-3-Clause; OpenJPEG BSD-2-Clause; libpng libpng-2.0; libtiff libtiff; zlib Zlib; AGG 2.3 permissive notice; fast_float MIT; simdutf MIT; project docs CC-BY-4.0. All are permissive and none imposes copyleft on this project, but several are outside the literal MIT/Apache/OFL list, so this is a recorded tooling exception pending DD-013, not a compliance claim. Redistributing the harness with the binary would require shipping these notices.

## Resolved packages

| Ecosystem / scope | Package | Version | Declared licence metadata |
| --- | --- | --- | --- |
| npm / frontend-runtime | [@babel/runtime](https://www.npmjs.com/package/@babel/runtime/v/7.29.7) | 7.29.7 | MIT |
| npm / build/test | [@oxc-project/types](https://www.npmjs.com/package/@oxc-project/types/v/0.150.0) | 0.150.0 | MIT |
| npm / build/test | [@playwright/test](https://www.npmjs.com/package/@playwright/test/v/1.63.0) | 1.63.0 | Apache-2.0 |
| npm / build/test | [@rolldown/binding-android-arm-eabi](https://www.npmjs.com/package/@rolldown/binding-android-arm-eabi/v/1.2.9) | 1.2.9 | MIT |
| npm / build/test | [@rolldown/binding-android-arm64](https://www.npmjs.com/package/@rolldown/binding-android-arm64/v/1.2.9) | 1.2.9 | MIT |
| npm / build/test | [@rolldown/binding-darwin-arm64](https://www.npmjs.com/package/@rolldown/binding-darwin-arm64/v/1.2.9) | 1.2.9 | MIT |
| npm / build/test | [@rolldown/binding-darwin-x64](https://www.npmjs.com/package/@rolldown/binding-darwin-x64/v/1.2.9) | 1.2.9 | MIT |
| npm / build/test | [@rolldown/binding-freebsd-x64](https://www.npmjs.com/package/@rolldown/binding-freebsd-x64/v/1.2.9) | 1.2.9 | MIT |
| npm / build/test | [@rolldown/binding-linux-arm-gnueabihf](https://www.npmjs.com/package/@rolldown/binding-linux-arm-gnueabihf/v/1.2.9) | 1.2.9 | MIT |
| npm / build/test | [@rolldown/binding-linux-arm64-gnu](https://www.npmjs.com/package/@rolldown/binding-linux-arm64-gnu/v/1.2.9) | 1.2.9 | MIT |
| npm / build/test | [@rolldown/binding-linux-arm64-musl](https://www.npmjs.com/package/@rolldown/binding-linux-arm64-musl/v/1.2.9) | 1.2.9 | MIT |
| npm / build/test | [@rolldown/binding-linux-ppc64-gnu](https://www.npmjs.com/package/@rolldown/binding-linux-ppc64-gnu/v/1.2.9) | 1.2.9 | MIT |
| npm / build/test | [@rolldown/binding-linux-s390x-gnu](https://www.npmjs.com/package/@rolldown/binding-linux-s390x-gnu/v/1.2.9) | 1.2.9 | MIT |
| npm / build/test | [@rolldown/binding-linux-x64-gnu](https://www.npmjs.com/package/@rolldown/binding-linux-x64-gnu/v/1.2.9) | 1.2.9 | MIT |
| npm / build/test | [@rolldown/binding-linux-x64-musl](https://www.npmjs.com/package/@rolldown/binding-linux-x64-musl/v/1.2.9) | 1.2.9 | MIT |
| npm / build/test | [@rolldown/binding-openharmony-arm64](https://www.npmjs.com/package/@rolldown/binding-openharmony-arm64/v/1.2.9) | 1.2.9 | MIT |
| npm / build/test | [@rolldown/binding-win32-arm64-msvc](https://www.npmjs.com/package/@rolldown/binding-win32-arm64-msvc/v/1.2.9) | 1.2.9 | MIT |
| npm / build/test | [@rolldown/binding-win32-x64-msvc](https://www.npmjs.com/package/@rolldown/binding-win32-x64-msvc/v/1.2.9) | 1.2.9 | MIT |
| npm / build/test | [@rolldown/pluginutils](https://www.npmjs.com/package/@rolldown/pluginutils/v/1.0.1) | 1.0.1 | MIT |
| npm / build/test | [@types/react](https://www.npmjs.com/package/@types/react/v/19.3.0) | 19.3.0 | MIT |
| npm / build/test | [@types/react-dom](https://www.npmjs.com/package/@types/react-dom/v/19.3.0) | 19.3.0 | MIT |
| npm / build/test | [@typescript/typescript-aix-ppc64](https://www.npmjs.com/package/@typescript/typescript-aix-ppc64/v/7.0.2) | 7.0.2 | Apache-2.0 |
| npm / build/test | [@typescript/typescript-darwin-arm64](https://www.npmjs.com/package/@typescript/typescript-darwin-arm64/v/7.0.2) | 7.0.2 | Apache-2.0 |
| npm / build/test | [@typescript/typescript-darwin-x64](https://www.npmjs.com/package/@typescript/typescript-darwin-x64/v/7.0.2) | 7.0.2 | Apache-2.0 |
| npm / build/test | [@typescript/typescript-freebsd-arm64](https://www.npmjs.com/package/@typescript/typescript-freebsd-arm64/v/7.0.2) | 7.0.2 | Apache-2.0 |
| npm / build/test | [@typescript/typescript-freebsd-x64](https://www.npmjs.com/package/@typescript/typescript-freebsd-x64/v/7.0.2) | 7.0.2 | Apache-2.0 |
| npm / build/test | [@typescript/typescript-linux-arm](https://www.npmjs.com/package/@typescript/typescript-linux-arm/v/7.0.2) | 7.0.2 | Apache-2.0 |
| npm / build/test | [@typescript/typescript-linux-arm64](https://www.npmjs.com/package/@typescript/typescript-linux-arm64/v/7.0.2) | 7.0.2 | Apache-2.0 |
| npm / build/test | [@typescript/typescript-linux-loong64](https://www.npmjs.com/package/@typescript/typescript-linux-loong64/v/7.0.2) | 7.0.2 | Apache-2.0 |
| npm / build/test | [@typescript/typescript-linux-mips64el](https://www.npmjs.com/package/@typescript/typescript-linux-mips64el/v/7.0.2) | 7.0.2 | Apache-2.0 |
| npm / build/test | [@typescript/typescript-linux-ppc64](https://www.npmjs.com/package/@typescript/typescript-linux-ppc64/v/7.0.2) | 7.0.2 | Apache-2.0 |
| npm / build/test | [@typescript/typescript-linux-riscv64](https://www.npmjs.com/package/@typescript/typescript-linux-riscv64/v/7.0.2) | 7.0.2 | Apache-2.0 |
| npm / build/test | [@typescript/typescript-linux-s390x](https://www.npmjs.com/package/@typescript/typescript-linux-s390x/v/7.0.2) | 7.0.2 | Apache-2.0 |
| npm / build/test | [@typescript/typescript-linux-x64](https://www.npmjs.com/package/@typescript/typescript-linux-x64/v/7.0.2) | 7.0.2 | Apache-2.0 |
| npm / build/test | [@typescript/typescript-netbsd-arm64](https://www.npmjs.com/package/@typescript/typescript-netbsd-arm64/v/7.0.2) | 7.0.2 | Apache-2.0 |
| npm / build/test | [@typescript/typescript-netbsd-x64](https://www.npmjs.com/package/@typescript/typescript-netbsd-x64/v/7.0.2) | 7.0.2 | Apache-2.0 |
| npm / build/test | [@typescript/typescript-openbsd-arm64](https://www.npmjs.com/package/@typescript/typescript-openbsd-arm64/v/7.0.2) | 7.0.2 | Apache-2.0 |
| npm / build/test | [@typescript/typescript-openbsd-x64](https://www.npmjs.com/package/@typescript/typescript-openbsd-x64/v/7.0.2) | 7.0.2 | Apache-2.0 |
| npm / build/test | [@typescript/typescript-sunos-x64](https://www.npmjs.com/package/@typescript/typescript-sunos-x64/v/7.0.2) | 7.0.2 | Apache-2.0 |
| npm / build/test | [@typescript/typescript-win32-arm64](https://www.npmjs.com/package/@typescript/typescript-win32-arm64/v/7.0.2) | 7.0.2 | Apache-2.0 |
| npm / build/test | [@typescript/typescript-win32-x64](https://www.npmjs.com/package/@typescript/typescript-win32-x64/v/7.0.2) | 7.0.2 | Apache-2.0 |
| npm / build/test | [csstype](https://www.npmjs.com/package/csstype/v/3.2.3) | 3.2.3 | MIT |
| npm / build/test | [detect-libc](https://www.npmjs.com/package/detect-libc/v/2.1.2) | 2.1.2 | Apache-2.0 |
| npm / build/test | [fdir](https://www.npmjs.com/package/fdir/v/6.5.0) | 6.5.0 | MIT |
| npm / build/test | [fsevents](https://www.npmjs.com/package/fsevents/v/2.3.3) | 2.3.3 | MIT |
| npm / frontend-runtime | [html-parse-stringify](https://www.npmjs.com/package/html-parse-stringify/v/4.0.1) | 4.0.1 | MIT |
| npm / frontend-runtime | [i18next](https://www.npmjs.com/package/i18next/v/26.4.2) | 26.4.2 | MIT |
| npm / build/test | [lightningcss](https://www.npmjs.com/package/lightningcss/v/1.33.0) | 1.33.0 | MPL-2.0 |
| npm / build/test | [lightningcss-android-arm64](https://www.npmjs.com/package/lightningcss-android-arm64/v/1.33.0) | 1.33.0 | MPL-2.0 |
| npm / build/test | [lightningcss-darwin-arm64](https://www.npmjs.com/package/lightningcss-darwin-arm64/v/1.33.0) | 1.33.0 | MPL-2.0 |
| npm / build/test | [lightningcss-darwin-x64](https://www.npmjs.com/package/lightningcss-darwin-x64/v/1.33.0) | 1.33.0 | MPL-2.0 |
| npm / build/test | [lightningcss-freebsd-x64](https://www.npmjs.com/package/lightningcss-freebsd-x64/v/1.33.0) | 1.33.0 | MPL-2.0 |
| npm / build/test | [lightningcss-linux-arm-gnueabihf](https://www.npmjs.com/package/lightningcss-linux-arm-gnueabihf/v/1.33.0) | 1.33.0 | MPL-2.0 |
| npm / build/test | [lightningcss-linux-arm64-gnu](https://www.npmjs.com/package/lightningcss-linux-arm64-gnu/v/1.33.0) | 1.33.0 | MPL-2.0 |
| npm / build/test | [lightningcss-linux-arm64-musl](https://www.npmjs.com/package/lightningcss-linux-arm64-musl/v/1.33.0) | 1.33.0 | MPL-2.0 |
| npm / build/test | [lightningcss-linux-x64-gnu](https://www.npmjs.com/package/lightningcss-linux-x64-gnu/v/1.33.0) | 1.33.0 | MPL-2.0 |
| npm / build/test | [lightningcss-linux-x64-musl](https://www.npmjs.com/package/lightningcss-linux-x64-musl/v/1.33.0) | 1.33.0 | MPL-2.0 |
| npm / build/test | [lightningcss-win32-arm64-msvc](https://www.npmjs.com/package/lightningcss-win32-arm64-msvc/v/1.33.0) | 1.33.0 | MPL-2.0 |
| npm / build/test | [lightningcss-win32-x64-msvc](https://www.npmjs.com/package/lightningcss-win32-x64-msvc/v/1.33.0) | 1.33.0 | MPL-2.0 |
| npm / build/test | [nanoid](https://www.npmjs.com/package/nanoid/v/3.3.19) | 3.3.19 | MIT |
| npm / build/test | [picocolors](https://www.npmjs.com/package/picocolors/v/1.1.1) | 1.1.1 | ISC |
| npm / build/test | [picomatch](https://www.npmjs.com/package/picomatch/v/4.0.7) | 4.0.7 | MIT |
| npm / build/test | [playwright](https://www.npmjs.com/package/playwright/v/1.63.0) | 1.63.0 | Apache-2.0 |
| npm / build/test | [playwright-core](https://www.npmjs.com/package/playwright-core/v/1.63.0) | 1.63.0 | Apache-2.0 |
| npm / build/test | [postcss](https://www.npmjs.com/package/postcss/v/8.5.28) | 8.5.28 | MIT |
| npm / frontend-runtime | [react](https://www.npmjs.com/package/react/v/19.3.0) | 19.3.0 | MIT |
| npm / frontend-runtime | [react-dom](https://www.npmjs.com/package/react-dom/v/19.3.0) | 19.3.0 | MIT |
| npm / frontend-runtime | [react-i18next](https://www.npmjs.com/package/react-i18next/v/17.0.15) | 17.0.15 | MIT |
| npm / build/test | [rolldown](https://www.npmjs.com/package/rolldown/v/1.2.9) | 1.2.9 | MIT |
| npm / frontend-runtime | [scheduler](https://www.npmjs.com/package/scheduler/v/0.28.0) | 0.28.0 | MIT |
| npm / build/test | [source-map-js](https://www.npmjs.com/package/source-map-js/v/1.2.1) | 1.2.1 | BSD-3-Clause |
| npm / build/test | [tinyglobby](https://www.npmjs.com/package/tinyglobby/v/0.2.17) | 0.2.17 | MIT |
| npm / frontend-runtime | [typescript](https://www.npmjs.com/package/typescript/v/7.0.2) | 7.0.2 | Apache-2.0 |
| npm / frontend-runtime | [use-sync-external-store](https://www.npmjs.com/package/use-sync-external-store/v/1.7.0) | 1.7.0 | MIT |
| npm / build/test | [vite](https://www.npmjs.com/package/vite/v/8.3.0) | 8.3.0 | MIT |
| pypi / runtime/test | [alembic](https://pypi.org/project/alembic/1.20.0/) | 1.20.0 | MIT |
| pypi / runtime/test | [annotated-doc](https://pypi.org/project/annotated-doc/0.0.5/) | 0.0.5 | MIT |
| pypi / runtime/test | [annotated-types](https://pypi.org/project/annotated-types/0.8.0/) | 0.8.0 | MIT |
| pypi / runtime/test | [anyio](https://pypi.org/project/anyio/4.15.1/) | 4.15.1 | MIT |
| pypi / runtime/test | [asn1crypto](https://pypi.org/project/asn1crypto/1.5.1/) | 1.5.1 | MIT |
| pypi / runtime/test | [boto3](https://pypi.org/project/boto3/1.43.99/) | 1.43.99 | Apache-2.0 |
| pypi / runtime/test | [botocore](https://pypi.org/project/botocore/1.43.99/) | 1.43.99 | Apache-2.0 |
| pypi / test | [certifi](https://pypi.org/project/certifi/2026.7.22/) | 2026.7.22 | MPL-2.0 |
| pypi / test | [cffi](https://pypi.org/project/cffi/2.1.1/) | 2.1.1 | MIT-0 |
| pypi / test | [charset-normalizer](https://pypi.org/project/charset-normalizer/3.5.1/) | 3.5.1 | MIT |
| pypi / runtime/test | [click](https://pypi.org/project/click/8.5.0/) | 8.5.0 | BSD-3-Clause |
| pypi / test | [colorama](https://pypi.org/project/colorama/0.4.6/) | 0.4.6 | Not declared; review LICENSE/classifiers |
| pypi / test | [cryptography](https://pypi.org/project/cryptography/50.0.1/) | 50.0.1 | Apache-2.0 OR BSD-3-Clause |
| pypi / runtime/test | [fastapi](https://pypi.org/project/fastapi/0.141.1/) | 0.141.1 | MIT |
| pypi / runtime/test | [greenlet](https://pypi.org/project/greenlet/3.5.6/) | 3.5.6 | MIT AND PSF-2.0 |
| pypi / runtime/test | [h11](https://pypi.org/project/h11/0.16.0/) | 0.16.0 | MIT |
| pypi / test | [httpcore](https://pypi.org/project/httpcore/1.0.9/) | 1.0.9 | BSD-3-Clause |
| pypi / test | [httpx](https://pypi.org/project/httpx/0.28.1/) | 0.28.1 | BSD-3-Clause |
| pypi / runtime/test | [idna](https://pypi.org/project/idna/3.20/) | 3.20 | BSD-3-Clause |
| pypi / test | [iniconfig](https://pypi.org/project/iniconfig/2.3.0/) | 2.3.0 | MIT |
| pypi / runtime/test | [jmespath](https://pypi.org/project/jmespath/1.1.0/) | 1.1.0 | MIT |
| pypi / runtime/test | [Mako](https://pypi.org/project/Mako/1.4.1/) | 1.4.1 | MIT |
| pypi / runtime/test | [MarkupSafe](https://pypi.org/project/MarkupSafe/3.0.3/) | 3.0.3 | BSD-3-Clause |
| pypi / test | [moto](https://pypi.org/project/moto/5.2.3/) | 5.2.3 | Apache-2.0 |
| pypi / test | [packaging](https://pypi.org/project/packaging/26.3/) | 26.3 | Apache-2.0 OR BSD-2-Clause |
| pypi / runtime/test | [pg8000](https://pypi.org/project/pg8000/1.31.5/) | 1.31.5 | BSD 3-Clause License |
| pypi / test | [pluggy](https://pypi.org/project/pluggy/1.6.0/) | 1.6.0 | MIT |
| pypi / test | [py-partiql-parser](https://pypi.org/project/py-partiql-parser/0.6.3/) | 0.6.3 | MIT |
| pypi / test | [pycparser](https://pypi.org/project/pycparser/3.0/) | 3.0 | BSD-3-Clause |
| pypi / runtime/test | [pydantic](https://pypi.org/project/pydantic/2.13.5/) | 2.13.5 | MIT |
| pypi / runtime/test | [pydantic_core](https://pypi.org/project/pydantic_core/2.46.5/) | 2.46.5 | MIT |
| pypi / test | [Pygments](https://pypi.org/project/Pygments/2.21.0/) | 2.21.0 | BSD-2-Clause |
| pypi / test | [pytest](https://pypi.org/project/pytest/9.1.1/) | 9.1.1 | MIT |
| pypi / runtime/test | [python-dateutil](https://pypi.org/project/python-dateutil/2.9.0.post0/) | 2.9.0.post0 | Dual License |
| pypi / test | [PyYAML](https://pypi.org/project/PyYAML/6.0.3/) | 6.0.3 | MIT |
| pypi / test | [requests](https://pypi.org/project/requests/2.34.2/) | 2.34.2 | Apache-2.0 |
| pypi / test | [responses](https://pypi.org/project/responses/0.26.3/) | 0.26.3 | Apache-2.0 |
| pypi / test | [ruff](https://pypi.org/project/ruff/0.16.8/) | 0.16.8 | MIT |
| pypi / runtime/test | [s3transfer](https://pypi.org/project/s3transfer/0.19.2/) | 0.19.2 | Apache License 2.0 |
| pypi / runtime/test | [scramp](https://pypi.org/project/scramp/1.4.17/) | 1.4.17 | MIT No Attribution |
| pypi / runtime/test | [six](https://pypi.org/project/six/1.17.0/) | 1.17.0 | MIT |
| pypi / runtime/test | [SQLAlchemy](https://pypi.org/project/SQLAlchemy/2.0.54/) | 2.0.54 | MIT |
| pypi / runtime/test | [starlette](https://pypi.org/project/starlette/1.6.0/) | 1.6.0 | BSD-3-Clause |
| pypi / runtime/test | [typing-inspection](https://pypi.org/project/typing-inspection/0.4.4/) | 0.4.4 | MIT |
| pypi / runtime/test | [typing_extensions](https://pypi.org/project/typing_extensions/4.16.0/) | 4.16.0 | PSF-2.0 |
| pypi / runtime/test | [urllib3](https://pypi.org/project/urllib3/2.8.0/) | 2.8.0 | MIT |
| pypi / runtime/test | [uvicorn](https://pypi.org/project/uvicorn/0.53.0/) | 0.53.0 | BSD-3-Clause |
| pypi / test | [Werkzeug](https://pypi.org/project/Werkzeug/3.1.8/) | 3.1.8 | BSD-3-Clause |
| pypi / test | [xmltodict](https://pypi.org/project/xmltodict/1.0.4/) | 1.0.4 | MIT |

## Container inputs

| Input | Manifest digest |
| --- | --- |
| Python 3.13 slim Bookworm | `sha256:2325bb286ec344af3e5898cc224b5844e2707ac6e26b1632516fd3edc84a5e26` |
| Node 22 Bookworm slim (build stage) | `sha256:48e4b67d85f87bd551df43704e24d252f56cc5f8e9718841aace50f19948f0f9` |
| PostgreSQL 17 Bookworm | `sha256:639ab7ceb90e13123085b741fb31ef493fba25463002f6da665352e7b534b652` |

These are multi-platform manifests read from the registry, not evidence that the images have been built, executed, scanned or redistributed. Development tools and base OS files retain their upstream notices. Product licence and contribution agreement remain undecided.

## Implementation references consulted

- [Docker startup ordering](https://docs.docker.com/compose/how-tos/startup-order/): healthy and completed-successfully dependencies.
- [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html): ordered migrations and connection-based configuration.
- [FastAPI containers](https://fastapi.tiangolo.com/deployment/docker/): application container deployment.
- [PostgreSQL licence](https://www.postgresql.org/about/licence/): separate licence identifier.

## Installation-time licence flags (2026-09-23)

The locked frontend and backend test dependencies were installed for validation. Installation was not blocked by the project allow-list; these items remain flagged for review under DD-013/DD-022:

- Frontend: `lightningcss@1.33.0` declares MPL-2.0; `picocolors@1.1.1` declares ISC; `source-map-js@1.2.1` declares BSD-3-Clause.
- Backend test graph: `certifi==2026.7.22` declares MPL-2.0. `httpx` declares BSD-3-Clause, while several installed distributions expose no simple `License` metadata and require upstream LICENSE/classifier review (including `cffi`, `click`, `colorama`, `cryptography`, `greenlet`, `idna`, `MarkupSafe`, `packaging` and `Werkzeug`).

These are review flags, not approval or a claim of compliance. The exact package versions remain pinned in the lockfiles; no dependency was substituted to hide a licence expression.

## OCR/layout candidate feasibility review (2026-09-24)

The candidate distributions were inspected with `pip download --no-deps` only; they were not installed into the application environment and were not added to either lockfile.

| Candidate | Version | Direct metadata | Evidence and remaining gate |
| --- | --- | --- | --- |
| `docling` | 2.130.0 | No licence value in wheel metadata; depends on `docling-slim[standard]==2.130.0` | The wrapper is not a self-contained runtime. The slim dependency graph, model files and their licences, CPU compatibility and PageModel coverage still require a controlled spike. |
| `paddleocr` | 3.7.0 | Apache License 2.0; depends on `paddlex[ocr-core]>=3.7.0,<3.8.0` | The direct declaration does not establish the licence or CPU/runtime suitability of PaddleX, native dependencies, language packs or model weights. No model download or execution was performed. |
| `pytesseract` | 0.3.13 | Apache License 2.0; depends on `packaging` and `Pillow` | This is a Python adapter, not the Tesseract engine. A separately installed Tesseract binary and language data would need isolation, version and licence review. |

Consequently, E8-03 and E8-04 remain partial and E8-08 remains a capability registry/contract rather than an installed-engine claim. The local deterministic extraction path and explicit unavailable-OCR state remain the supported offline behavior until the dependency, model, sandbox and acceptance evidence is complete. See DD-160.

## Strict scan

Run `python scripts/check_licenses.py` from the repository root to scan the checked-in dependency inventory, emit `artifacts/sbom.cdx.json` and `artifacts/license-report.json`, and fail on unknown, compound or non-MIT/Apache-2.0/OFL metadata. `--allow-findings` is available only to produce evidence while the policy decision is unresolved; it must not be used as a compliance claim. The GitHub Actions workflow runs the strict command and uploads both reports even when the check fails.
