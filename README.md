# Evaluation Data Inspector

**From evaluation data to transparent, evidence-based reports.**

[Open the live application](https://evaluation-data-inspector.streamlit.app/) · [Deployment guide](DEPLOYMENT.md)

Evaluation Data Inspector is a professional Streamlit reporting tool for adult researchers, educators, and evaluators. It converts a CSV or XLSX workbook into a deterministic, **APA 7–aligned academic report** with data-quality findings, descriptive statistics, charts, and matching DOCX/printable HTML exports. It does not claim guaranteed APA compliance and is not a clinical, regulatory, or confidential-data environment.

## What ships

- CSV support for UTF-8/UTF-8 BOM plus explicit GB18030, comma, semicolon, and tab options.
- Lazy XLSX worksheet selection with bounded ZIP inspection and cached-formula disclosure.
- Guardrails of 10 MiB, 100,000 rows, 250 columns, and 2,000,000 parsed cells.
- Conservative identifier, numeric, categorical, ordinal, date, and text role inference with overrides.
- Original missingness and non-finite numeric exclusions reported separately; duplicates are flagged, never deleted.
- Numeric summaries (finite *n*, *M*, sample *SD*, median, minimum, maximum) and categorical frequencies using valid observations as the denominator.
- User-selected group, Pearson relationship, paired pre/post, and date-mean reporting with explicit assumptions and unavailable-result reasons.
- Stable chart rules and chart budgets: Brief ≤3, Standard ≤5, Detailed ≤8.
- Complete deterministic reporting in English, Simplified Chinese, Spanish, and Finnish.
- Optional overview, quality, descriptive, figure, and interpretation sections; provenance and essential limitations always remain.
- Variable inclusion, conservative role overrides, unique user-reviewed display labels, optional units, and user-supplied valid-range flags (values are never removed automatically).
- One report model used by the continuous preview, editable DOCX, and standalone UTF-8 HTML.
- Optional, opt-in Gemini connective prose. Python remains authoritative for every statistic, chart, table, caption, factual sentence, and reference number.

## Statistical boundaries

This release is descriptive. It does not calculate hypothesis tests, *p* values, confidence intervals, regression, causal effects, imputation, survey weights, or automatic outlier removal.

- Numeric summaries exclude infinity separately from original missingness and use sample *SD* (`ddof=1`).
- Cohen's *d* preserves first-observed group minus second-observed group order and is produced only for exactly two explicitly confirmed independent groups, with at least two valid observations per group and positive pooled variance.
- Pearson *r* uses pairwise-complete finite observations (*n* ≥ 3) with nonzero variance. It describes linear association; significance and causation are not inferred.
- Paired change is `post − pre` on the identical complete-pair subset. Positive change is not called improvement unless the user supplies scale direction (the current UI does not assume it).
- Date reporting aggregates duplicate dates by mean and count, sorts chronologically, and does not interpolate.
- Category tables display up to 20 categories and combine the remainder as `Other` without renormalising the displayed percentages.

## Local setup

Python 3.12 is the deployment target.

```bash
git clone https://github.com/DrWangZezhao/evaluation-data-inspector.git
cd evaluation-data-inspector
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
streamlit run app.py
```

Open `http://localhost:8501`. Use the included CSV/XLSX examples or upload a synthetic, non-confidential file.

## Optional Gemini writing

Template reporting is the default and is complete without external services. AI writing is hidden/disabled unless all required operator configuration is present:

```toml
# .streamlit/secrets.toml (never commit this file)
GEMINI_API_KEY = "replace-with-a-real-key"
GEMINI_MODEL = "gemini-3.1-flash-lite"
GEMINI_PAID_SERVICE = "true"
```

`GEMINI_PAID_SERVICE=true` is an operator declaration, not something inferred from the key. Set it only after establishing the billing-linked Gemini Developer API service required for public use in the EEA, Switzerland, and the UK. The app never configures billing.

The adapter uses the official `google-genai` SDK, one request per report with at most one validation/transient correction, a 25-second per-attempt timeout, and a 4,000-token output cap. It applies best-effort limits of five attempts per session/hour and 60 attempts per process/hour; process counters reset on restart and are not durable spending caps. Configure provider quotas and billing alerts separately.

Before an AI request, the application deterministically selects at most 30 aggregate facts, suppresses detailed facts based on fewer than five observations, and defaults to aliases. It does not send raw rows, identifiers, filenames, individual dates, raw text cells, or chart arrays. This minimisation is not a guarantee of anonymisation. Google/hosting retention remains governed by their infrastructure and terms.

Advanced settings include a concise payload preview showing the request language/audience/depth, sharing choices, and the aggregate-only boundary; the validated fact IDs used by a completed AI request are recorded in technical notes.

The default model is the explicit `gemini-3.1-flash-lite`, not a floating alias. Sources reviewed 2026-10-01: [pricing](https://ai.google.dev/gemini-api/docs/pricing), [model](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite), [lifecycle](https://ai.google.dev/gemini-api/docs/deprecations), [terms](https://ai.google.dev/gemini-api/terms), and [structured output](https://ai.google.dev/gemini-api/docs/structured-output). At that review, standard text rates were USD 0.25/million input tokens and USD 1.50/million output tokens (including thinking), and the lifecycle page listed 2027-05-07 as the earliest shutdown date. Recheck the official pages before enabling paid use later. The app never silently substitutes a model; unavailable AI falls back to templates.

AI responses are schema-checked, bound to complete `[[FACT:id]]` sentences, and screened for unknown facts, free quantitative claims, unsupported significance/causal language, and invented references. These are safeguards, not a claim that semantic validation is hallucination-proof.

## Exports

DOCX contains editable text, tables, and the exact PNG figures shown in the preview. Standalone HTML contains inline CSS and embedded figures, with no scripts, trackers, or remote assets. To create a PDF, open the downloaded HTML in a browser and choose **Print → Save as PDF**. Client fonts and pagination can vary; there is intentionally no server-side PDF conversion.

Charts bundle `NotoSansCJKsc-Regular.otf` under the SIL Open Font License 1.1 in `assets/fonts/`. Chinese DOCX exports set East Asian metadata and embed the same OFL font so recipients do not need a system CJK font; this intentionally makes the Chinese DOCX larger. Latin-language exports use normal document font references.

## Testing

```bash
pytest -q
python -m compileall -q app.py analysis.py inspector
python -m pip check
```

Provider calls are mocked or avoided in normal tests. Tests cover legacy analysis behavior, parsing safety, workbook selection, limits, roles, exclusions, known-answer statistics, chart budgets/rendering, four-language template generation, evidence validation, suppression, DOCX/HTML consistency, hostile-label escaping, and fallback behavior.

## Architecture

```text
parse → validate → infer/override roles → calculate → facts/chart specs
      → optional validated narrative → one ReportDocument → preview/DOCX/HTML
```

`analysis.py` retains its public import contract. `inspector/pipeline.py` is independent of Streamlit. Uploaded bytes, parsed frames, reports, and downloads stay in `st.session_state`; they are not put in cross-session Streamlit caches. The shared rate counter contains timestamps only.

## Privacy and limitations

The application does not intentionally write uploads, prompts, reports, or model responses to disk or logs. “No intentional persistence by this app” does not mean local-only processing or zero retention by Streamlit, Google, a browser, or network infrastructure. Use synthetic or approved non-confidential data only.

Role inference, deterministic templates, and language checks cannot establish measurement validity or replace expert statistical and language review. Finnish/Spanish availability tests are not expert academic-language certification.

## Docker

```bash
docker build -t evaluation-data-inspector:latest .
docker run --rm -p 8501:8501 evaluation-data-inspector:latest
```

The image runs as non-root and includes the application modules and licensed font assets. See [DEPLOYMENT.md](DEPLOYMENT.md) for Streamlit Community Cloud configuration, verification, and rollback. AWS Lightsail remains an optional documented appendix only; this upgrade does not create AWS resources.
