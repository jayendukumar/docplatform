# Ten-minute quickstart

This path verifies the current self-hosted HTML/API foundation. It does not claim the E14-01 PDF acceptance criterion: the selected rendering artifact is deterministic HTML until a PDF engine is evaluated, licensed and validated.

## 1. Start the platform

From the repository root:

```powershell
$env:PLATFORM_HTTP_PORT = '8001'
docker compose up -d
Invoke-WebRequest -UseBasicParsing http://localhost:8001/health/ready
```

The readiness response should be HTTP 200. The default host port is 8000; the example uses 8001 when that port is already occupied.

## 2. Open the generated API explorer

Visit [OpenAPI explorer](http://localhost:8001/docs) or download [OpenAPI JSON](http://localhost:8001/openapi.json). The specification is generated from the running FastAPI application.

## 3. Render the bundled sample

List the templates and copy the ID of the published `Welcome letter` template:

```powershell
$templates = Invoke-RestMethod http://localhost:8001/api/templates
$template = $templates.items | Where-Object { $_.name -eq 'Welcome letter' }
$template.id
```

Render a candidate artifact:

```powershell
$body = @{ data = @{ recipient = @{ name = 'Ada' }; rows = @(@{ description = 'Example'; amount = 12.5 }); show_note = $true } } | ConvertTo-Json -Depth 8
$render = Invoke-RestMethod -Method Post -Uri "http://localhost:8001/api/templates/$($template.id)/render" -ContentType 'application/json' -Body $body
New-Item -ItemType Directory -Force .\artifacts | Out-Null
$render.artifact | Set-Content .\artifacts\quickstart.html
```

Open `artifacts/quickstart.html` in a browser. For a durable render, submit `POST /api/jobs` with `kind: render` and poll the returned status URL; Compose enables the bounded render/extraction supervisor.

## 3a. Generate a PDF from the browser workspace

Open the workspace at `http://localhost:8000/`, choose **Explore template**, then click **Save draft** if you changed the template. Click **Generate PDF**. The editor saves the current draft, calls `POST /api/templates/{template_id}/render-pdf`, displays the returned PDF in an embedded browser viewer, and provides **Download PDF**. The report remains labelled as a candidate until rendering and native-reader acceptance are complete.

## 4. Produce the offline PDF candidate

The repository includes a reproducible Chromium candidate wrapper. It disables browser network requests and writes the PDF, manifest and screenshot locally:

```powershell
npm --prefix frontend ci
npx --prefix frontend playwright install chromium
python scripts/quickstart_pdf_candidate.py artifacts/quickstart.html
```

The wrapper fails if Chromium does not produce a non-empty PDF and manifest, and reports the rendering elapsed time. The output is `artifacts/quickstart-candidate.pdf`. Its manifest labels the artifact as a candidate and records that fonts and native-reader review are still pending. This command is evidence tooling, not a production PDF endpoint.

## Current acceptance boundary

The commands above prove Compose startup, readiness, generated OpenAPI, a deterministic HTML render and a reproducible offline Chromium PDF candidate. They do not prove production PDF output, native-reader approval, font embedding or final output fidelity. Those remain tracked as partial E6/E14-01 work until a rendering engine decision and evidence-backed PDF validation are recorded.
