# Exam Backend

FastAPI + Firestore backend for the Ŋwà' GCE exam-prep platform.

## What it does

- **Auth**: email/password and Google sign-in (Firebase ID token exchange),
  password reset via email (Resend). Custom JWTs with `student` / `editor` / `admin` roles.
- **Exam content pipeline**: editors upload scanned exam PDFs, pages are rendered
  and sent to Gemini for structured extraction, reviewed in the portal, then
  normalized into Firestore collections (`subjects`, `topics`, `questions`,
  `subquestions`, `sub_subquestions`, `diagrams`, `figures`, `exam_metadata`).
- **Exam PDF storage**: Firebase Storage (private) with short-lived signed URLs.
- **Team management**: admin-only CRUD of editor/admin accounts.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env   # then fill in real values
.venv/bin/uvicorn app.main:app --reload
```

## Tests & lint

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
```

## Deployment

GitHub Actions deploys `main` to Cloud Run (`exam-portal-api`) using the
`DEPLOY_ENV_YAML` secret for environment variables. `ENVIRONMENT=production`
makes the app refuse to boot without a real `SECRET_KEY`.
