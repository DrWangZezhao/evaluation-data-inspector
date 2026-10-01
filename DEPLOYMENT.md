# Deployment and operations

## Primary: Streamlit Community Cloud

The production target is the existing application:

- URL: <https://evaluation-data-inspector.streamlit.app/>
- Repository: `DrWangZezhao/evaluation-data-inspector`
- Branch: `main`
- Entry point: `app.py`
- Python: 3.12

The application is fully functional in deterministic template mode without secrets. A push to `main` should trigger the existing Community Cloud integration, but a Git push alone is not proof of deployment. In Streamlit **Manage app → Settings**, verify the repository/branch/entry point above, especially after a GitHub repository transfer.

### Optional Gemini configuration

In **Manage app → Settings → Secrets**, add only after a billing-linked Gemini Developer API project is established:

```toml
GEMINI_API_KEY = "replace-with-a-real-key"
GEMINI_MODEL = "gemini-3.1-flash-lite"
GEMINI_PAID_SERVICE = "true"
```

Never put a real key in Git, logs, chat, an example file, or Docker build context. `GEMINI_MODEL` is optional and defaults to `gemini-3.1-flash-lite`; an unavailable configured model falls back to deterministic templates without a paid substitution. `GEMINI_PAID_SERVICE` defaults to false.

For public Gemini use in the EEA, Switzerland, and UK, the reviewed provider terms required a billing-linked service. Configure Gemini account quotas and billing alerts separately. Application counters are best-effort and reset when the process restarts.

### Deployment verification

After a rebuild completes:

1. Open the public URL in a signed-out/incognito browser and confirm it does not require an unintended viewer login.
2. Confirm the new subtitle, CSV/XLSX uploader, four languages, primary **Generate report** button, and collapsed Advanced settings.
3. Generate the synthetic CSV template report and download both DOCX and HTML.
4. Upload `sample_data/synthetic_evaluation_workbook.xlsx`, select each usable worksheet, and generate a report.
5. Change a setting after generation and confirm the old preview/downloads are unavailable until regeneration.
6. Upload malformed input and confirm a safe, nontechnical error.
7. Check a narrow/mobile viewport.
8. If Gemini is intentionally configured, make one bounded synthetic request and record the requested/returned model without logging the prompt, response, or key.

The Streamlit health endpoint is useful but insufficient on its own:

```bash
curl --fail https://evaluation-data-inspector.streamlit.app/_stcore/health
```

Also inspect real page content and generate/download behavior.

### Rollback

The pre-upgrade rollback reference is `342ac7410880c5e7cb0524ab3065864def304a3a`.

Prefer a normal revert so history remains auditable:

```bash
git pull --ff-only origin main
git log --oneline --max-count=5
git revert <upgrade-commit-sha>
git push origin main
```

Do not force-push. After the revert, observe the Community Cloud rebuild and repeat the public verification steps.

## Local container verification

```bash
docker build -t evaluation-data-inspector:latest .
docker run --rm -p 8501:8501 --name evaluation-data-inspector evaluation-data-inspector:latest
curl --fail http://127.0.0.1:8501/_stcore/health
```

The Docker image runs as UID 10001, bundles the `inspector/` package and Noto CJK font/license, and excludes tests, local secrets, `.env` files, and generated reports.

## Optional existing AWS Lightsail path

AWS is not the primary target and this upgrade does not create resources. If an operator deliberately chooses the previous container path, build the same image, publish it to an existing approved registry/service, configure secrets through the platform rather than the image, verify the health endpoint and real UI, and remove unused resources to stop charges. Exact account, region, IAM, networking, TLS, and cleanup choices belong to the operator; this repository does not claim an AWS deployment has been performed.
