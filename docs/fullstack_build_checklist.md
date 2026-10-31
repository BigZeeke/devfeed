# Full-Stack Web App Build Checklist

My repeatable order for building and testing a full-stack app: build from the data outward, and don't move to the next layer until the current one is verified, not just written. Deploy early: a working skeleton on the real server beats a finished app that only runs on my laptop.

## DevFeed status (as of Oct 31, 2026)

1. Steps 1–3: done and verified on real Postgres. Both required third-party APIs are integrated as management commands (`ingest_hacker_news`, `ingest_github`), each verified idempotent.
2. Step 4: done. CRUD API for sources, tags and articles, with PUT mutation, PUT/DELETE idempotency, nested tag updates and input validation covered by tests. `DEBUG` now comes from `.env` and defaults to False (PR #38), so production returns Django's generic 500 page instead of a traceback.
3. Second full-CRUD resource changed from votes to bookmarks (new Bookmark model: saved articles with a note and a per-user read flag) after instructor review. Votes stay as a feature.
4. Step 5: done (PR #26). DRF token auth with register, log-in (token) and log-out endpoints. Sources, tags and articles are readable by anyone and writable only by staff.
5. Step 6: done. Owner-scoped full CRUD on keywords and bookmarks (PR #30), article voting (PR #32), and search autocomplete on tags, parameterized through a `field` param (PR #34).
6. Step 7 in progress: 102 automated tests pass (23 ingestion, 7 permissions, 10 auth, 12 article endpoints, 11 bookmarks, 11 keywords, 10 votes, 10 search, 8 environment config). Sources and tags are still covered only through the permission tests.
7. Step 8: items 1–4 done (PR #38). `DEBUG`, `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS` now come from `.env`; the full git-history secret search found no live secrets (results on issue #37); `django-cors-headers` allows the React dev server origins. Items 5–6 (NGINX layout, `VITE_API_URL`) stay open under issue #13 for the Docker and deploy steps.
8. Next: Docker (Step 9), then the React shell (Step 10). Steps 9–17 not started. First deploy (step 11) targeted for Week 23 Day 3. Presentation Week 24 Day 4.
9. Open question: GitHub results are unfiltered and can include off-topic or NSFW repositories; decide on filtering before the presentation.

## 1. Proposal & ERD

1. **Done:** Diagram entities, attributes, and relationships in drawdb.app (cardinality: one-to-many, many-to-many, etc.)
2. **To do:** Justify normalization decisions (e.g., why a join table exists instead of a flat text field)
3. **Done:** Mark primary keys, foreign keys, and any indexes worth adding upfront, especially fields I'll filter, sort, or search on
4. **Done:** Export/save the ERD as a real deliverable, not just sketched and discarded
5. **Done:** Design nested/related resources here too (e.g., a Class↔Student many-to-many, a Grade join model) before writing any code
6. **Done:** Identify at least two user-owned resources that will get full CRUD from the UI (for DevFeed: followed keywords and bookmarks)
7. **Done:** Pick the two third-party APIs and confirm each one actually works with a quick request (for DevFeed: Hacker News Algolia API, GitHub Search API)
8. **To do:** Sketch wireframes for every main page
9. **Done:** Write the MVP list and the stretch list, scoped against the real hour budget (~50 hours), not the calendar
10. **Done:** Submit the proposal

## 2. Data Model

1. **Done:** Translate the ERD into models (fields, types, relationships)
2. **Done:** Run migrations
3. **Done:** Open a shell and manually create/query one row per model
4. **Done:** Confirm relationships (ForeignKey, ManyToMany) work as expected in the shell
5. **Done:** Cross-check the migration output (`python manage.py sqlmigrate`, or inspect the schema directly) against the ERD to confirm what got built matches what I designed

## 3. Data Population (Ingestion or Seed Data)

1. **Done:** Write a script, management command, or fixture to load real or realistic data
2. **Done:** Wrap each required third-party API in its own management command, so both are integrated, not just tested standalone
3. **Done:** Run each command once
4. **Done:** Query the database directly (not through the app) to confirm rows exist
5. **Done:** Confirm field values look correct (types, nulls, formatting)
6. **Done:** Run each command a second time and confirm it creates no duplicates (idempotent)

## 4. Backend API (CRUD)

1. **Done:** Write serializers for each model
2. **Done:** Write viewsets/routes for GET, POST, PUT/PATCH, DELETE
3. **Done:** Register routes in urls.py
4. **Done:** Test every endpoint with `curl` or Postman at `http://127.0.0.1:8000` before touching any client code
5. **Done:** Confirm GET returns real data from step 3
6. **Done:** Confirm POST/PUT/DELETE actually mutate the database (re-check with step 3's query method) (POST verified with curl and psql; PUT and DELETE covered by tests in `test_article_endpoints.py`)
7. **Done:** Confirm error cases return sensible status codes (400, 404, etc.) without leaking internals (no raw stack traces or SQL in the response) (validation errors return 400 and a second DELETE returns 404, both covered by tests; `DEBUG` defaults to False since PR #38, so a 500 returns Django's generic error page instead of a traceback; no test forces a 500)
8. **Done:** Handle nested/related resources: creating, updating, and deleting nested objects through the API, not just flat single-model CRUD (tags through `tag_labels`: set on create, replaced by PUT, kept by PATCH without it, cleared by an empty list; covered by tests)
9. **Done:** Keep response shape consistent across endpoints (same field naming, same pagination wrapper) so clients don't need special-case parsing per endpoint
10. **Done:** Paginate list endpoints from the start, even with a small dataset; it's cheap now and painful to retrofit later
11. **Done:** Confirm PUT/DELETE are idempotent: calling one twice produces the same end state as calling it once (covered by tests: a repeated PUT leaves the same state; a second DELETE returns 404 and changes nothing)
12. **Done:** Validate/sanitize input on the backend even though the frontend also validates; the API is the real gate, not the UI (covered by tests: missing required fields, malformed URL, duplicate URL, unknown source, and tag labels over 100 characters all return 400)

## 5. Auth

Auth comes before feature endpoints because user-owned resources (votes, keywords) need a logged-in user.

1. **Done:** Use Django's built-in `User` and DRF token auth (`rest_framework.authtoken`; `TokenAuthentication` is the DRF default)
2. **Done:** Sign-up endpoint: validates with Django's password validators, creates the user, returns a token (`/api/auth/register/`; covered by tests, including weak password and duplicate username)
3. **Done:** Log-in endpoint: returns a token for valid credentials, 400 otherwise (`/api/auth/token/`; covered by tests)
4. **Done:** Log-out endpoint: deletes the user's token (`/api/auth/logout/`, returns 204; covered by tests, including that a deleted token can't be reused)
5. **Done:** Confirm protected endpoints reject unauthenticated requests (anonymous writes return 401; covered by tests)
6. **Done:** Confirm a valid token grants access and an invalid one doesn't (covered by tests; an invalid token is rejected even for reads)
7. **Done:** Confirm authenticated ≠ authorized: a regular user's token can't hit staff-only endpoints just because it's valid (regular users get 403 on writes; covered by tests)
8. **Done:** Lock down data that ingestion owns (for DevFeed: sources, tags, articles) so only staff can write to it (`IsStaffOrReadOnly` is the default permission class)

## 6. User-Owned Resources & Feature Endpoints

1. **Done:** Full CRUD on each user-owned resource, scoped so users only see and change their own rows (for DevFeed: keywords and bookmarks) (`/api/keywords/` and `/api/bookmarks/`, PR #30; another user's row returns 404; covered by tests)
2. **Done:** Set the owner from `request.user` on create; never trust an owner id from the request body (`HiddenField(CurrentUserDefault())` on both serializers, PR #30)
3. **Done:** Design non-CRUD endpoints as parameterized from the start (e.g., a `fields` param on search) so adding scope later doesn't require reworking the endpoint (`/api/search/autocomplete/` takes a `field` param backed by a lookup table, so a new field only adds an entry; PR #34)
4. **Done:** Build the narrowest working version first (e.g., autocomplete on tags only, a simple up/down vote counter) before expanding scope (search supports tags only, PR #34; voting is an up/down counter with one row per user and article, PR #32)
5. **Done:** Confirm each endpoint composes cleanly with pagination and response-shape conventions from step 4 (keyword, bookmark and search lists use the default pagination wrapper; search returns the same shape as `/api/tags/`, covered by tests)
6. **Done:** Note any feature that implies a future ML/re-ranking layer (e.g., vote-driven ranking) as a stretch goal, not part of this pass (vote-driven ranking is listed under Optional Next Steps; votes aren't used in ranking yet)

## 7. Automated Tests for the API

1. **Partial:** Write tests for each endpoint (happy path + at least one failure case) (partial: articles, auth, keywords, bookmarks, votes and search covered; sources and tags only through the permission tests)
2. **Done:** Include tests for sign-up/log-in/log-out, ownership (one user can't read or change another's rows), feature endpoints, and auth-protected routes (sign-up/log-in/log-out, auth-protected routes, ownership for keywords and bookmarks, and the vote and search endpoints are covered; CORS headers and the `.env` list parser are covered too)
3. **Done:** Assert on what the API returns (behavior), not on internal method calls, so refactoring doesn't break tests unnecessarily (API tests check status codes, response data and database state)
4. **Done:** Run the test suite and confirm everything passes (102 tests pass on `main`: 23 ingestion, 7 permissions, 10 auth, 12 article endpoints, 11 bookmarks, 11 keywords, 10 votes, 10 search, 8 environment config)
5. **Done:** Deliberately break something (typo a field name, change a status code) and confirm a test catches it (done on ingestion code and on each API test file in PR #26, on the ownership and vote upsert tests in PRs #30 and #32, on case-insensitive search matching in PR #34, and on `CorsMiddleware` in PR #38)
6. **Done:** Fix the deliberate break, confirm tests pass again

## 8. Environment Config, CORS & Reverse Proxy

1. **Done:** Move every secret and setting into `.env` (`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL`, `POSTGRES_*`, `CORS_ALLOWED_ORIGINS`, API tokens), never hardcoded (every setting that exists so far comes from `.env`; `DEBUG`, `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS` moved in PR #38; `POSTGRES_*` get added with `docker-compose.yml` in Step 9)
2. **Done:** Commit a `.env.example` listing every variable with placeholder values; confirm `.env` is in `.gitignore`
3. **Done:** Search the git history for committed secrets; if any turn up, rotate them, don't just delete the line (full search of every commit on Oct 31 found no live secrets; the only committed secret was the old `SECRET_KEY`, already rotated; results on issue #37)
4. **Done:** Configure `django-cors-headers` so the React dev server (a different origin) can call the API (`CORS_ALLOWED_ORIGINS` from `.env`, `CorsMiddleware` first; checked with curl and covered by tests, PR #38)
5. **To do:** Plan the production layout: NGINX serves the React build and proxies `/api/` to the backend, so both share one origin
6. **To do:** Remember `VITE_API_URL` is baked in at `npm run build`, not read at runtime

## 9. Containerize (Docker)

1. **To do:** Write a Dockerfile for the backend (Gunicorn) and a multi-stage one for the frontend (Node build, then NGINX)
2. **To do:** Add a `.dockerignore` to each so `node_modules`, virtual environments and `.env` never end up in an image
3. **To do:** Write a `docker-compose.yml` with `db` (Postgres with a named volume and a real user/password), `backend` and `frontend`
4. **To do:** Build and run locally with Docker; confirm it behaves the same as my non-Docker local setup
5. **To do:** Run migrations inside the container (`docker compose exec backend python manage.py migrate`); don't assume they carry over
6. **To do:** Re-run the step 4–7 checks against the containerized version

## 10. React Frontend: Shell and Core Flow

1. **To do:** Set up the React project with Vite and Material UI (`@mui/material`, `@mui/icons-material`)
2. **To do:** One MUI theme (palette, typography, dark mode) instead of scattered CSS
3. **To do:** Add routing (React Router) and an app bar with navigation between every page
4. **To do:** Fetch from the API with loading and error states (TanStack Query or `useEffect`)
5. **To do:** Sign-up, log-in and log-out in the UI; store the token, send it on requests, handle a 401
6. **To do:** Share the logged-in user through Context
7. **To do:** Get one core flow working end to end against the real API (for DevFeed: the paginated feed)

## 11. First Deploy (Walking Skeleton)

1. **To do:** Set a $10 monthly AWS budget alert before launching anything
2. **To do:** Launch the EC2 instance; security group allows SSH from my IP only and HTTP from anywhere
3. **To do:** Install Docker and the Compose plugin
4. **To do:** Clone the repo, create `.env` from `.env.example` with production values
5. **To do:** `docker compose up -d --build`, then run migrations and `createsuperuser` inside the backend container
6. **To do:** Run the ingestion commands once on the server and confirm rows in Postgres
7. **To do:** Confirm the site loads from outside the instance and sign-up/log-in work on the live URL
8. **To do:** Ship it even if it's unfinished and ugly; production surprises (CORS, env vars, migrations) are cheaper to find now

## 12. React Feature Completion

1. **To do:** Build out full CRUD in the UI for each user-owned resource (list, create, edit, delete)
2. **To do:** Build the autocomplete search bar (debounced input, calls the endpoint from step 6)
3. **To do:** Build the voting UI (thumbs up/down, reflects the current vote per article)
4. **To do:** Manually click through every CRUD operation in the browser
5. **To do:** After each action, re-check the database directly to confirm nothing silently failed
6. **To do:** Redeploy after each feature lands, not all at the end

## 13. Production Hardening & Regression Pass

1. **To do:** Schedule ingestion on the server (cron calling the management commands)
2. **To do:** Re-run the step 4–7 checks against the deployed URL
3. **To do:** Click through every user flow in production, not only locally
4. **To do:** Confirm the database connection, migrations and env vars are correct on the server
5. **To do:** Set up basic logging so failures are visible after deployment
6. **To do:** Re-run the full automated test suite one more time before calling it done

## 14. Code Quality / Refactor Pass

1. **To do:** Check for N+1 query problems (looping over a queryset and hitting the DB per iteration); fix with `select_related`/`prefetch_related`
2. **To do:** Look for duplicated fetch/error-handling logic in the frontend that could live in one API module
3. **To do:** Confirm views stay thin: business logic lives in models/serializers/services, not sprawling across view functions
4. **To do:** Revisit any abstraction I added early: did I actually repeat this 2-3 times, or did I abstract before I needed to (YAGNI/KISS check)?
5. **To do:** Consistent formatting across the codebase (Black/Ruff for Python, Prettier for JS)
6. **To do:** Re-run the full test suite after any refactor to confirm behavior didn't change, only structure

## 15. Documentation & Presentation

1. **To do:** README: what the app does and the problem it solves, screenshots or a demo GIF, live link, setup steps someone can follow from `git clone`, technologies used, ERD
2. **To do:** Confirm the setup steps work from a fresh clone
3. **To do:** Record a backup demo walkthrough before presentation day
4. **To do:** Prepare the 5–10 minute presentation: what it does, live demo, tech stack, hardest problem debugged, what I'd do with another week
5. **To do:** Add the project to my LinkedIn and GitHub profile README once it's deployed

## 16. CI/CD (Optional, Exceeds Expectations)

1. **To do:** Set up GitHub Actions to run the backend test suite on every push/PR
2. **To do:** Add branch protection so merges require passing tests
3. **To do:** Set up continuous deployment so a merge to main triggers a deploy

## 17. Frontend E2E Tests (Optional)

1. **To do:** Write Playwright tests covering the core user flows (view list, create, edit, delete, search, vote)
2. **To do:** Include a test for the auth flow (sign up, log in, protected route redirect, log out)
3. **To do:** Run the suite against a real running backend, not a mock

## The Rules to Remember

1. **Verify against the layer below.** At every step, I check against the database, not just "the screen looked right," and I don't start the next layer until the current one is confirmed working. This holds through deployment: a container isn't "done" until it behaves the same as my tested local version, and a deployment isn't "done" until I've re-run my checks against the live URL.
2. **Deploy early, then keep deploying.** The first deploy happens once there's a working skeleton, not at the end. Every feature after that gets redeployed and checked in production.
3. **Watch for DRY, efficiency, and scope creep as I go, not just at the end.** Before marking any step done, I ask: did I duplicate logic I already wrote, is this the right query for the data size, and did I build only what this step needs? Step 14 is for what's hard to catch in the moment (N+1 queries, duplication), not a substitute for catching the obvious stuff early.
4. **Small commits, one PR per issue.** Clear commit messages throughout. Each PR description notes whether any code was materially AI-generated, and I can walk through every line I ship.

## Optional Next Steps (once the above is solid)

- **Second client (CLI):** a thin command-line client against the same API. Build it after the web MVP is deployed, then do a cross-client regression pass: change data in one client, confirm it shows in the other, and repeat in the opposite direction.
- **Raw HTML/CSS/JS checkpoint:** a single plain page with `fetch()` calls, as proof the API works from a browser with no framework. Useful for learning; skipped when the hour budget is tight.
- **GraphQL:** a single endpoint where the client asks for exactly the fields it wants, instead of many fixed-shape REST endpoints. Worth exploring as a stretch add-on once REST is solid.
- **AI/LLM integration:** embeddings/vector search, RAG (retrieval-augmented generation), and AI API integration into a Django backend, including using vote data to train a preference/re-ranking model instead of simple score-based filtering. A separate skill track from core full-stack CRUD, worth its own pass once the base app is deployed and stable.
