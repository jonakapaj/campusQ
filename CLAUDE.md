# CampusQ Albania

(Working name, rename freely.)

<project_context>
A social network only for Albanian university students and professors.
Everyone signs in with an academic email under `.edu.al`. Students join their
university's community, follow courses and people, share posts, and ask and
answer questions. Professors can join too. An admin verifies them, and their
answers carry a "Verified Professor" badge.

The goal is a real, deployed product with real users at Albanian universities,
which I'll also post about publicly while building it. Quality matters more
than speed: this repo is part of my public portfolio.

About me: I'm a working software engineer (Python/Django, React/Node, SQL),
based in Tirana. I'm building this to ship something useful and to sharpen my
Python and system design skills.
</project_context>

<how_to_work_with_me>
- You are a senior Django engineer pairing with me. Build with me, not for me.
- Work one feature at a time. Before writing code for a feature:
  1. Restate what you think the feature is in 1-2 sentences.
  2. Propose the approach: models, migrations, URLs, views, templates, tests.
  3. Flag any open question or tradeoff.
  4. Wait for my OK.
- After I approve, implement it, run the tests, run ruff and mypy, and fix
  everything until it's green. Then summarize what changed in a few bullets.
- Explain non-obvious decisions in a sentence or two, especially security,
  query performance and Django idioms I might not know.
- If something I ask for is a bad idea (security, privacy, scaling), say so
  directly and suggest the better option. Don't just comply.
- Don't add features, dependencies or abstractions I didn't ask for. If you
  think one is worth it, suggest it and let me decide.
- Keep commits small, with clear messages, so the history tells a story.
- At the end of a session, update the roadmap checkboxes below and suggest the
  next step.
</how_to_work_with_me>

<stack>
- Python 3.13 (pinned in `.python-version`), Django 5.2 LTS, managed with `uv`
- PostgreSQL 16 (Docker Compose for local dev)
- Django templates + HTMX + Tailwind (server-rendered, minimal JS)
- pytest + pytest-django, factory_boy
- ruff, mypy (django-stubs, strict)
- GitHub Actions CI
- Deploy: Render / Railway / Fly.io (decide at Milestone 5)
</stack>

<commands>
- First time: `cp .env.example .env` and set `DJANGO_SECRET_KEY`
- `docker compose up -d --wait`: start Postgres
- `uv run python manage.py runserver`
- `uv run pytest`
- `uv run ruff check . && uv run ruff format .`
- `uv run mypy .`
- Translations (requires `gettext`, e.g. `brew install gettext`):
  - extract: `uv run python manage.py makemessages -l sq --ignore='.venv/*' --no-location --no-obsolete`
  - compile: `uv run python manage.py compilemessages --ignore='.venv/*'` (`.mo` files are not committed)
  - check: `./scripts/check_translations.sh` (CI runs this; fails on stale, untranslated or fuzzy entries)
</commands>

<language>
- The UI is in **Albanian (sq) by default**, with English (en) as a second
  language. Use Django i18n from day one: wrap every user-facing string in
  `gettext` / `{% translate %}`. Never hardcode UI text.
- Source strings (msgids) are written in English; `locale/sq` holds the Albanian.
- The language comes only from the user's explicit choice (cookie), never the
  browser's Accept-Language, so English-configured phones still get Albanian.
  See `core/middleware.py`.
- Code, comments, commit messages and docs are in English.
- Support Albanian characters (ë, ç) everywhere: search, usernames, slugs.
</language>

<domain_model>
- **University**: name, short name (e.g. UT, UPT, UAMD), city, email domains
  (one university can have several, e.g. `unitir.edu.al` and
  `students.unitir.edu.al`), status: ACTIVE | PENDING
- **User**: custom user model from day one (email is the login)
  - role: STUDENT | PROFESSOR | ADMIN
  - professor_status: NONE | PENDING | VERIFIED | REJECTED
  - university (derived from the email domain)
  - profile: display name, avatar, faculty, field of study, year, bio
- **Faculty** / **Course**: belong to a University; courses have professors (M2M)
- **Follow**: users can follow users and courses
- **Post**: author, university, optional course, body (Markdown), images,
  type: POST | QUESTION, is_anonymous (questions only)
- **Comment** (on posts) / **Answer** (on questions): is_accepted (by the
  asker), is_endorsed (by a verified professor of that course)
- **Reaction / Vote**: one per user per target; users can't vote on their own content
- **Tag**, **Report**, **Notification**
</domain_model>

<rules>
Signup and email:
- Only emails whose domain ends with `.edu.al` can sign up. Match on the full
  domain after `@`, lowercased, and check that it actually ends in `.edu.al`
  (so `x@fake-edu.al` and `x@edu.al.evil.com` are rejected).
- If the domain belongs to a known University, link the user to it.
- If it's an unknown `.edu.al` domain, allow signup but create a PENDING
  University for an admin to confirm and name.
- Some Albanian institutions may use domains outside `.edu.al`. Keep an
  admin-managed allowlist for those exceptions. Never hardcode domains in code.
- The email must be verified before the user can post, comment or vote.

Roles:
- Everyone signs up as a STUDENT. "I'm a professor" creates a PENDING request.
  An admin approves or rejects it on a review page.
- Only VERIFIED professors get the badge and can endorse answers, and only in
  courses they teach.
- Never trust the client for role or permission checks. Enforce permissions in
  views and querysets, and test them.

Privacy and safety (users are mostly young students):
- Anonymous questions hide the author from other students. Professors of the
  course and admins can see them. Store the author, never expose it in HTML,
  API responses or notifications to students.
- Profiles are visible only to logged-in, verified users. No public indexing
  of user content until I decide otherwise.
- Users can delete their account and their data.
- Rate-limit signup, login, posting and reporting.
- Every report goes to a moderation queue. Admins can hide content and suspend users.
</rules>

<code_quality>
- Every feature ships with tests, including permission tests (a student must
  never get professor or admin powers, and a user from one university must not
  see another university's private content).
- Watch for N+1 queries. Use select_related / prefetch_related and mention it
  when you do.
- Prefer simple, boring Django: function or class-based views, forms, the ORM.
  No premature microservices, no extra JS frameworks.
- Settings via environment variables (`config/env.py`). Secrets never committed.
</code_quality>

<decisions>
Agreed before Milestone 1 (2026-11-24):
- Auth: django-allauth, with the domain policy plugged into a custom
  `AccountAdapter.clean_email()`. Its built-in signup/login rate limits cover
  part of Milestone 5.
- Email domains live in a `UniversityDomain(domain unique, university FK)` table.
  That table **is** the allowlist: a domain outside `.edu.al` is accepted only
  if an admin has added it.
- Domains match exactly. No inferring a university from a parent domain; unknown
  subdomains go to the admin queue with a hint about the parent.
- An unknown `.edu.al` domain creates a PENDING University only **after** the
  email is verified, so unverifiable junk domains never reach the admin queue.
- Settings: a small env helper, no django-environ. A local `.env` is loaded
  without overriding real environment variables.
- `AUTH_USER_MODEL` must exist before the first `migrate`. Don't run
  `migrate` until the custom User model lands (slice 1b).

Known email domains (researched 2026-11-24; verify before seeding):
- University of Tirana: students get `name_surname.<faculty>student@unitir.edu.al`
  (faculty code is in the local part, not a subdomain). Confirmed on unitir.edu.al.
- Polytechnic University of Tirana: website moved to `upt.edu.al`, but staff
  addresses seen in 2025-26 notices are `@upt.al`. That needs an allowlist row.
  Student format unconfirmed.
- Other public universities (Medicine, Agricultural, Arts, Sports, Shkodër,
  Elbasan, Vlorë, Korçë, Gjirokastër, Durrës): domains not yet confirmed.
  The official list is at arsimi.gov.al and ascal.al.
- UBT (`ubt-uni.net`) and University of Prishtina are in Kosovo, outside scope.
</decisions>

<roadmap>
1. [x] **Foundation**: project setup, i18n (sq/en), custom User, University +
       `.edu.al` domain check, signup/login, email verification (console
       email backend locally), CI
       - [x] 1a skeleton: uv, settings via env, Postgres compose, i18n, tooling, CI
       - [x] 1b custom User, University, UniversityDomain, admin
       - [x] 1c domain policy + signup/login (allauth)
       - [x] 1d email verification + verified-only guard
2. [ ] **Profiles & communities**: profiles, university and course pages,
       follow users and courses
3. [ ] **Feed & posts**: posts with Markdown and images, comments, reactions,
       home feed (followed courses, people and your university)
4. [ ] **Q&A**: questions, answers, accepted answers, anonymous-to-peers,
       code highlighting
5. [ ] **Roles & trust**: professor request flow, admin review page, badges,
       endorsements, reports + moderation queue, rate limiting. **Deploy publicly.**
6. [ ] **Growth**: notifications, Postgres full-text search (with Albanian
       characters), seed/demo data, landing page in Albanian, README with
       screenshots + architecture diagram
7. [ ] **Stretch**: background tasks for email/notifications, real-time
       updates, "similar questions" when asking, events for student
       associations, a PWA so it feels like an app on phones
</roadmap>
