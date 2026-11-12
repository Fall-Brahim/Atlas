# AtlasCloud - Engineering Guide

## Project purpose

AtlasCloud is a small professional Internal Developer Platform (IDP), built
progressively over the long term. Its purpose is to help development teams
create organizations and projects, choose application templates, and eventually
deploy, build, operate, and observe applications.

The project is also a practical demonstration of backend engineering, cloud
engineering, DevOps, infrastructure automation, architecture, observability,
and security. Deployment, CI/CD, resource monitoring, logs, metrics, and
availability checks are future capabilities, not current guarantees.

## Current stack

The repository is a Django modular monolith:

- Python 3.14.8 in the local `.atlas` virtual environment.
- Django 6.1.2.
- Django REST Framework 3.18.3 is installed, but no REST API surface is
  currently exposed by `config/urls.py`.
- Django Templates.
- `django-tailwind` 4.6.0 with Tailwind CSS 4.3.3.
- SQLite in `db.sqlite3` for initial development.
- Git and GitHub for source control.
- Docker may be available on the developer workstation, but Docker is not
  integrated into the application yet.

Dependencies are pinned in `requirements.txt`. Do not describe a package as an
application integration merely because it is installed.

## Architecture and repository structure

AtlasCloud uses a modular monolith. The main structure is:

```text
apps/
├── accounts/          # Custom users and authentication
├── organizations/     # Organizations, memberships, and permissions
├── projects/          # Organization-scoped project lifecycle
└── templates_catalog/ # Reusable application template catalog
config/                # Django settings, URLs, WSGI, and ASGI
templates/             # Shared Django layout
static/                # Project static assets and template icons
theme/                 # Django Tailwind application and source CSS
infrastructure/        # Reserved for future infrastructure code
```

`accounts.User` is the custom user model. Authentication uses email instead of
username. `organizations` owns the `Organization` and `Membership` models and
the OWNER, ADMIN, and MEMBER authorization rules. `projects` stores projects
belonging to exactly one organization and records their creator. The template
catalog stores versioned, validated application definitions and provides
authenticated browsing, search, filtering, details, and a “use” flow; it does
not deploy an application yet. `config` wires the installed applications and
URL routes. `theme`, shared templates, and static assets provide the current
server-rendered frontend.

## Implemented functionality

### Accounts

- Custom `User` model with unique email authentication.
- Registration, login, POST-only logout, and protected dashboard.
- Django password hashing and configured password validators.
- Duplicate email validation and Django authentication compatibility.

### Frontend

- Shared Django template layout and dashboard navigation.
- Django Tailwind integration with Tailwind CSS 4.
- Responsive/collapsible sidebar.
- Persistent light/dark theme preference using browser storage.

### Organizations

- Creation, listing, details, settings, and controlled deletion.
- Membership management with OWNER, ADMIN, and MEMBER roles.
- Adding existing users by email, role changes, member removal, and member
  departure.
- Ownership integrity protection and organization-scoped authorization.
- Cross-organization access isolation.

### Projects

- Creation, organization-scoped listing, details, and updates.
- DRAFT, ACTIVE, and ARCHIVED lifecycle states.
- Archival and restoration.
- Slug uniqueness within an organization.
- Permanent deletion intentionally disabled.
- Optional association with an application template.

### Template catalog

- Versioned `ApplicationTemplate` records with one active version per slug.
- Categories, technology metadata, configuration schema validation, and
  protection against secret-like fields.
- Seeded catalog data and Django Admin management.
- Authenticated list, search, category filter, detail, and selection pages.

### Not implemented

There is currently no deployment engine, Docker image build/publish workflow,
GitHub integration, CI/CD pipeline, runtime resource monitoring, application
logs/metrics, availability monitoring, or audit-log module.

## Architectural rules

### Users and ownership

- Use `settings.AUTH_USER_MODEL` for every user relationship; never reference
  `auth.User` directly.
- Every project belongs to exactly one organization. A project must not be
  owned directly by an individual user.
- Project permissions derive from organization membership. Do not introduce a
  separate project-role system without explicit architectural justification.

### Authorization and integrity

- Enforce authorization server-side on every organization and project action.
- Never trust organization IDs, project IDs, or role values supplied by the
  client without validation and authorization.
- Prevent IDOR and cross-organization data leakage by scoping lookups to the
  authenticated user's memberships.
- Use foreign keys, constraints, indexes, and transactions where appropriate.
- Do not rely only on frontend validation.
- Do not delete/recreate the database for ordinary development problems.
- Do not delete or rewrite migrations without explicit approval and a justified
  migration plan.

## Engineering standards

Inspect the repository before modifying it. Preserve the existing architecture,
keep views and modules focused, use meaningful names, and avoid unnecessary
abstraction or premature microservices. Use Django Forms and the ORM for
validation and persistence, handle errors explicitly, avoid duplicated
authorization logic, and add meaningful automated tests. Do not add
dependencies or refactor unrelated modules without justification.

Use Django Templates, the existing shared layout, Django Tailwind, and the
existing light/dark theme. Do not introduce React, Vue, Bootstrap, or
traditional custom CSS for ordinary styling.

Important technical decisions should be explained in French. Code identifiers,
URLs, and technical conventions remain in English.

## Development workflow and validation

For a significant feature: inspect the repository, analyze the problem,
propose the architecture, obtain approval for significant architectural
changes, implement incrementally, test, perform a security review, update
documentation, and report delivery results.

Run applicable commands from the project virtual environment and report their
actual results:

```bash
.atlas/bin/python manage.py check
.atlas/bin/python manage.py test
.atlas/bin/python manage.py check --deploy
.atlas/bin/python manage.py makemigrations --check
.atlas/bin/python manage.py tailwind build
git diff --check
```

`check --deploy` is expected to require production environment settings. A
passing local `check` is not evidence that production configuration is ready.

## Roadmap

| Module | Responsibility | Status |
|---|---|---|
| Accounts | Authentication and users | Implemented |
| Organizations | Organizations and memberships | Implemented |
| Projects | Project management | Implemented |
| Templates Catalog | Versioned application templates and selection | Implemented (catalog foundation) |
| Deployments | Application deployment lifecycle | Planned |
| Pipelines | Image builds, publishing, and CI/CD | Planned |
| Observability | Metrics, logs, and availability | Planned |
| Audit Logs | Activity history | Planned |

The roadmap can evolve as the architecture develops. The template catalog's
current selection page must not be described as a deployment workflow until
deployments are implemented.
