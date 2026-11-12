# AtlasCloud

AtlasCloud is an internal developer platform built as a modular Django monolith.

## Local development

The project currently targets Python 3.14 and Django 6.1.

```bash
python -m venv .atlas
source .atlas/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
set -a; source .env; set +a
python manage.py migrate
python manage.py tailwind dev
```

The application reads configuration from environment variables. The shell
commands above load the local `.env` file for the current session.
`.env.example` documents the available settings; do not commit a real `.env`
file.

## Tailwind frontend

The centralized `theme` application owns the Tailwind CSS v4 configuration for
the whole project. Its `@source` directive scans the shared templates and all
application templates, including `apps/accounts/templates/`.

Install the Python and frontend dependencies once:

```bash
python -m pip install -r requirements.txt
cd theme/static_src
npm install
cd ../..
```

During development, use:

```bash
python manage.py tailwind dev
```

This runs Django and the Tailwind watcher together. The shared
`templates/base.html` loads the generated stylesheet with `{% tailwind_css %}`.
The watcher recompiles it when scanned templates or `styles.css` change.

For production, compile a minified stylesheet as a separate build step and do
not run the development watcher:

```bash
python manage.py tailwind build
python manage.py collectstatic --noinput
```

The compiled file is written to `theme/static/css/dist/` and is intentionally
ignored by Git. It must be generated during deployment before collecting
static files. `node_modules/` is also ignored and must not be committed.

## User architecture

AtlasCloud uses `apps.accounts.User`, a custom model based on Django's
`AbstractUser`. The email address is unique and is the authentication
identifier; the inherited username field is intentionally removed.

`CustomUserManager` preserves Django's password hashing and provides the
standard `create_user` and `create_superuser` APIs. The model also retains
`is_active`, `is_staff`, `is_superuser`, groups, and permissions for Django
authentication and Admin compatibility.

Other applications must reference the user model through
`settings.AUTH_USER_MODEL` in model relationships, for example:

```python
from django.conf import settings
from django.db import models

owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
```

Changing the user model after production data exists is a complex migration.
This model was introduced before application-specific data existed, so the
disposable local SQLite database was recreated once and migrated from scratch.

## Web authentication

The accounts application provides:

- `/accounts/register/` for account creation;
- `/accounts/login/` for email and password authentication;
- `/accounts/logout/` as a POST-only action;
- `/accounts/dashboard/` as an authenticated example page.

Registration uses a Django form and the configured password validators. Password
hashing is delegated to the custom user model's `set_password()` method.
Django's `LoginView` handles authentication and validates the `next` parameter
before redirecting. Protected views use `login_required`.

## Organizations

The `apps.organizations` module models collaborative workspaces with two
tables: `Organization` and `Membership`. A membership links one user to one
organization and carries one of three roles: `OWNER`, `ADMIN`, or `MEMBER`.
Memberships reference `settings.AUTH_USER_MODEL`, and the database enforces one
membership per user and organization plus at most one owner per organization.

Organizations are created through the web flow in a transaction, which creates
the organization and the creator's owner membership together. The initial
implementation deliberately does not support ownership transfer: the owner
cannot be removed, demoted, or leave the organization. This preserves the
single-owner invariant until a dedicated transfer workflow is introduced.

Permissions are enforced server-side:

- owners can edit, manage members, and delete their organization;
- admins can edit settings and manage members, but cannot modify admins or the owner;
- members can view the organization and leave it, but cannot edit settings or members.

Organization-specific lookups always filter through the authenticated user's
membership, preventing access by guessing another organization's slug.

Owners and admins can add existing users from an organization's detail page.
The operation accepts only `MEMBER` and `ADMIN`, resolves accounts by
case-insensitive email, rejects duplicate memberships, and uses the existing
database uniqueness constraint as the final integrity guarantee. Invitations and
ownership transfer are intentionally outside this module's scope.

The application root (`/`) redirects anonymous users to login and authenticated
users to the dashboard. The shared layout provides navigation to organizations
and a light/dark theme toggle. The selected theme is stored in the browser's
`localStorage` and falls back to the operating system preference.

## Projects

The `apps.projects` module associates projects with organizations and records
their creator for traceability. Project slugs are unique within an
organization, and projects use `DRAFT`, `ACTIVE`, and `ARCHIVED` lifecycle
states. Organization members can view and create projects; owners and admins
can edit, archive, and restore them. Permanent deletion is intentionally not
available so future deployments, pipelines, logs, and audit records can remain
associated with a project.

Project URLs always resolve the organization through the current user's
membership before loading a project. This prevents cross-organization access
by changing URL slugs.

## Template catalog

The `apps.templates_catalog` module stores reusable, platform-level
application and infrastructure template definitions. Each template is
versioned by `(slug, version)`, and the database allows only one active
version for a given slug. Inactive versions remain available for future
deployment history without being shown to regular users.

Authenticated users can browse active templates at `/templates/`, search by
name, slug, description, or technology metadata, filter by category, and view
template details. Catalog definitions are managed through Django Admin using
global Django permissions; organization roles do not grant catalog
modification rights.

The initial catalog includes Django Application, FastAPI Application, Node.js
Application, Static Website, PostgreSQL Database, and Redis Cache. These
entries are inserted by the data migration
`apps/templates_catalog/migrations/0002_seed_initial_templates.py`.

The catalog entries are currently metadata definitions, not executable
application generators. They do not yet contain source repositories, Docker
build instructions, or deployment behavior. The selected template and its
configuration schema provide the foundation for a future project bootstrap
and deployment engine.

Template metadata includes a public technology stack and a lightweight JSON
configuration schema. These fields describe future deployment inputs but are
not executed by this module and must never contain secrets or credentials.
Future deployments will reference a specific template version with
`on_delete=PROTECT`, keeping historical deployment references stable.

New projects must select an active catalog template during creation. The
selected template version is stored on the project and displayed in project
details. Existing projects created before catalog selection remain compatible
with a nullable reference and can be assigned a template later.

The template detail page also provides a `Use this template` action. It first
asks the authenticated user to choose one of their organizations, then opens
the project creation form with the selected template prefilled. This is the
first step of the future application configuration workflow; it does not yet
generate source code, build an image, or deploy an application.

## Application navigation

After authentication, the Dashboard is the application home. It provides an
overview of the user's organizations and links to each workspace. Authenticated
pages use a responsive sidebar on larger screens and a compact menu on mobile.
The sidebar exposes only the Dashboard, Organizations, and the current
workspace context; it never becomes a long list of organizations. A collapse
button turns it into an icon rail and remembers the preference in the browser.
The account email, theme switcher, and POST-only logout are grouped in the user
area instead of being repeated in page content.

## Validation

```bash
python manage.py check
python manage.py test
```
# Atlas
# Atlas
