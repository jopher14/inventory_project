# IT Asset Inventory

A Django web application for tracking company IT equipment, recording asset audits, and managing employee accountability documents.

## Features

- Track laptops, monitors, cellphones, and other equipment with type-specific specifications.
- Record company tags, unique serial numbers, assignees, purchase dates, and asset status.
- Search inventory by company tag, serial number, or unit name.
- Generate QR codes containing the company tag, serial number, and unit name.
- Look up assets by scanned tag and record audit remarks with an auditor and timestamp.
- Export inventory audit reports as CSV or PDF and download QR labels as a PNG grid.
- Generate accountability PDFs by assignee and upload signed scans.
- Manage user accounts, roles, passwords, and active status.
- Serve QR images and accountability scans through an authenticated media endpoint.

Asset statuses: **Available**, **Assigned**, **Under Repair**, and **Disposed**.

## Roles

| Capability | ADMIN | IT | AUDIT |
| --- | --- | --- | --- |
| View and search inventory | Yes | Yes | Yes |
| Add, edit, and delete assets | Yes | Yes | No |
| Generate accountability PDFs and upload scans | Yes | Yes | No |
| Export QR label grid | Yes | Yes | No |
| Scan assets and record audits | Yes | No | Yes |
| Export CSV/PDF audit reports | Yes | No | Yes |
| Manage application user accounts | Yes | No | No |

Django superusers bypass application role checks. Access to Django's separate `/admin/` site also depends on Django staff permissions.

## Technology

- Python and Django (`Django>=4.2,<5.0` in `requirements.txt`)
- PostgreSQL, with environment-based database configuration
- Bootstrap, Django Crispy Forms, and Crispy Bootstrap 5
- Pillow and qrcode for QR images
- ReportLab for PDF generation
- Gunicorn and WhiteNoise for deployment
- Ruff and Django's test runner for checks

The GitHub Actions workflow uses **Python 3.12**.

## Local setup

### 1. Clone and install

```bash
git clone https://github.com/jopher14/inventory_project.git
cd inventory_project
python -m venv .venv
```

Activate the virtual environment:

**Windows PowerShell**

```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configure the environment

Create a `.env` file beside `manage.py`:

```dotenv
SECRET_KEY=replace-with-a-generated-secret
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=your_database
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_HOST=your_database_host
DB_PORT=5432
```

Generate a secret with:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Use a PostgreSQL database that accepts SSL connections, such as Supabase. The current settings require SSL for both database configuration paths.

Alternatively, set `DATABASE_URL`; it takes precedence over the individual `DB_*` variables:

```dotenv
DATABASE_URL=postgresql://user:password@host:5432/database
```

URL-encode special characters in credentials when using a database URL. Keep real secrets out of Git; `.env` is already ignored.

### 3. Initialize and run

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) and sign in with the superuser account. Create additional accounts from the application's user management page.

## Configuration reference

| Variable | Purpose / default |
| --- | --- |
| `SECRET_KEY` | Required Django secret key |
| `DEBUG` | Defaults to `False`; use `True` for local development |
| `ALLOWED_HOSTS` | Comma-separated hosts; defaults to `localhost,127.0.0.1` |
| `DATABASE_URL` | Preferred database connection URL when provided |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` | Required when no database URL is supplied outside tests |
| `DB_PORT` | Defaults to `5432` |
| `MEDIA_ROOT` | Upload and QR storage directory; defaults to the repository's `media/` directory |
| `DJANGO_SUPERUSER_USERNAME` | Build script bootstrap username; defaults to `admin` |
| `DJANGO_SUPERUSER_EMAIL` | Build script bootstrap email; defaults to `admin@example.com` |
| `DJANGO_SUPERUSER_PASSWORD` | Required by `build.sh` when no superuser exists |

Render's `RENDER_EXTERNAL_HOSTNAME` is added to allowed hosts automatically. Application timestamps use `Asia/Manila`.

## Typical workflow

1. An ADMIN or IT user adds an asset and its specifications.
2. The application generates its QR code.
3. Assign equipment to an employee using the **Assigned To** field.
4. Generate an accountability form for the assignee and upload the signed scan.
5. An ADMIN or AUDIT user scans or enters the company tag and submits audit remarks.
6. Export audit reports or print a QR label grid as needed.

Mobile camera scanning requires browser camera permission and a secure context, normally HTTPS or localhost.

## Checks and tests

Set `SECRET_KEY` in your environment or `.env`, then run:

```bash
ruff check .
ruff format --check .
python manage.py test
```

The Django test command uses an isolated, in-memory SQLite database. It does not require the production PostgreSQL credentials. Existing tests cover authentication forms, login behavior, and basic model behavior.

## Render deployment

The repository includes [render.yaml](render.yaml) for a Python web service, PostgreSQL database, and persistent media disk.

1. Create a Render Blueprint from this repository.
2. Supply `DJANGO_SUPERUSER_PASSWORD` when prompted.
3. Optionally configure `DJANGO_SUPERUSER_USERNAME` and `DJANGO_SUPERUSER_EMAIL`.
4. Review the service and database configuration before deploying.

The configured commands are:

```text
Build: ./build.sh
Start: gunicorn inventory_project.wsgi:application
```

The build script installs dependencies, collects static files, applies migrations, and creates a superuser only if none exists.

The Blueprint sets `MEDIA_ROOT=/var/data/media` and mounts persistent storage at `/var/data`. Preserve this storage across deployments so QR codes and uploaded scans remain available. Back up both the database and media files.

### CI/CD

[GitHub Actions](.github/workflows/ci-cd.yml) runs Ruff and Django tests for pushes and pull requests targeting `main` or `master`.

After successful checks on a push to either branch, it calls a Render deployment hook. To use that step, configure the GitHub Actions repository secret:

```text
RENDER_DEPLOY_HOOK_URL
```

Choose a deployment trigger strategy that avoids duplicate deployments if Render automatic deploys are also enabled.

## Project structure

```text
inventory/
  models.py          # Users, assets, specifications, and audit logs
  forms.py           # Authentication, user creation, and asset forms
  views.py           # Inventory, audit, reporting, users, and protected media
  utils.py           # QR label grid export
  urls.py            # Application routes
  templates/         # Inventory, login, user management, and audit pages
  static/            # Application CSS, JavaScript, and images
  migrations/        # Database migrations
  tests/             # Django tests
inventory_project/
  settings.py        # Environment, database, authentication, and storage settings
  urls.py            # Root routes and media endpoint
media/               # QR images and uploaded scans
static/              # Additional project static assets
staticfiles/         # Collected deployment static files
.github/workflows/   # CI/CD workflow
build.sh             # Deployment initialization
render.yaml          # Render Blueprint
manage.py            # Django management commands
requirements.txt     # Python dependencies
pyproject.toml       # Ruff configuration
```

## Troubleshooting

- **Missing environment variable:** provide `SECRET_KEY` and either `DATABASE_URL` or the required `DB_*` values before running management commands.
- **Database connection failure:** verify credentials, network access, and SSL support.
- **Missing QR images or scans after deployment:** check `MEDIA_ROOT` and the persistent disk; database records alone do not contain the file contents.
- **Media request returns 403 or redirects to login:** sign in with an authorized account. Media is served through the application.
- **Camera does not open:** check HTTPS, browser permissions, and device camera availability.
