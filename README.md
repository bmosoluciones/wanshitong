# WanShiTong

> A lightweight, private knowledge-management system.

Store, organise, and share Markdown documents inside your team.

---

## Features

- Role-based access control: **admin**, **editor**, **read-only**
- Document lifecycle: *draft* → *public* → *archived*
- Per-document ACL
- Markdown editor with live preview
- Version history with one-click restore
- Hierarchical categories and free-form tags
- CSRF protection on all forms
- Password hashing with Argon2

---

## Requirements

| Requirement | Minimum version |
|---|---|
| Python | 3.11 |
| pip | 22+ |

Key Python dependencies (see `requirements.txt` for the full list):

| Package | Purpose |
|---|---|
| Flask | Web framework |
| Flask-SQLAlchemy | ORM (SQLite in development, PostgreSQL/MySQL in production) |
| Flask-Login | Session management |
| Flask-WTF | CSRF-protected forms |
| Flask-Babel | Internationalisation (i18n) |
| Flask-Session | Server-side sessions |
| argon2-cffi | Password hashing |
| Markdown + bleach | Markdown rendering with XSS sanitisation |
| python-ulid | ULID primary keys |
| waitress | WSGI server for production |

---

## Development setup

```bash
# 1. Clone the repository
git clone https://github.com/bmosoluciones/wanshitong.git
cd wanshitong

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # Linux / macOS
# .venv\Scripts\activate       # Windows PowerShell

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) set environment variables
export SECRET_KEY="change-me"          # Required in production
export DATABASE_URL="sqlite:///app.db" # Defaults to SQLite
export ADMIN_USER="app-admin"          # Default admin username
export ADMIN_PASSWORD="app-admin"      # Default admin password

# 5. Start the development server
python app.py
```

The server starts at <http://127.0.0.1:8080>.
Log in with the admin credentials configured above (default: `app-admin` / `app-admin`).

---

## Running tests

```bash
# Install dependencies (if not already installed)
pip install -r requirements.txt

# Run the full test suite
pytest

# Run with verbose output
pytest -v

```

Tests use an **in-memory SQLite database** so no external services are required.

---

## Configuration

The application reads configuration from environment variables.
A file-based config (`app.conf`) is also supported — see `wanshitong/config.py` for search paths.

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `dev` | Flask secret key — **change in production** |
| `DATABASE_URL` | SQLite file | SQLAlchemy database URI |
| `ADMIN_USER` | `app-admin` | Username for the automatically created admin account |
| `ADMIN_PASSWORD` | `app-admin` | Password for the automatically created admin account |
| `SESSION_REDIS_URL` | *(unset)* | Redis URL for session storage (defaults to SQLAlchemy sessions) |

---

## Internationalisation (i18n)

The application ships with **Spanish** (default) and **English** translations.
The active locale is resolved in this order:

1. `lang` query parameter (`?lang=en`, `?lang=es`)
2. `lang` key stored in the user session
3. Browser `Accept-Language` header
4. Default: `es` (Spanish)

To recompile translations after editing `.po` files:

```bash
# From the repository root
pybabel compile -d wanshitong/translations
```

To extract new strings and update existing catalogs (sources are inside the
`wanshitong` package):

```bash
# From the repository root
# babel.cfg is written relative to the `wanshitong` source dir passed below
pybabel extract -F babel.cfg -k lazy_gettext -o wanshitong/translations/messages.pot wanshitong
pybabel update -i wanshitong/translations/messages.pot -d wanshitong/translations
pybabel compile -d wanshitong/translations
```

---

## License

Apache-2.0 — see [LICENSE](LICENSE).
