# Full-Stack Web App Build Checklist

My repeatable order for building and testing a full-stack app: build from the data outward, and don't move to the next layer until the current one is verified, not just written. Deploy early: a working skeleton on the real server beats a finished app that only runs on my laptop.

## DevFeed status (as of Oct 10, 2026)

1. Steps 1–4: done and verified on real Postgres (ERD, models, HN ingestion, CRUD API for sources, tags and articles).
2. Step 3 follow-up: `ingest_github` command for the GitHub Search API is next. It's the second required third-party API.
3. Steps 5–17: not started. Proposal (step 1 deliverables) due Week 22 Day 2. First deploy (step 11) targeted for Week 23 Day 3. Presentation Week 24 Day 4.

## 1. Proposal & ERD

- [ ] Diagram entities, attributes, and relationships in drawdb.app (cardinality: one-to-many, many-to-many, etc.)
- [ ] Justify normalization decisions (e.g., why a join table exists instead of a flat text field)
- [ ] Mark primary keys, foreign keys, and any indexes worth adding upfront, especially fields I'll filter, sort, or search on
- [ ] Export/save the ERD as a real deliverable, not just sketched and discarded
- [ ] Design nested/related resources here too (e.g., a Class↔Student many-to-many, a Grade join model) before writing any code
- [ ] Identify at least two user-owned resources that will get full CRUD from the UI (for DevFeed: followed keywords and votes)
- [ ] Pick the two third-party APIs and confirm each one actually works with a quick request (for DevFeed: Hacker News Algolia API, GitHub Search API)
- [ ] Sketch wireframes for every main page
- [ ] Write the MVP list and the stretch list, scoped against the real hour budget (~50 hours), not the calendar
- [ ] Submit the proposal

## 2. Data Model

- [ ] Translate the ERD into models (fields, types, relationships)
- [ ] Run migrations
- [ ] Open a shell and manually create/query one row per model
- [ ] Confirm relationships (ForeignKey, ManyToMany) work as expected in the shell
- [ ] Cross-check the migration output (`python manage.py sqlmigrate`, or inspect the schema directly) against the ERD to confirm what got built matches what I designed

## 3. Data Population (Ingestion or Seed Data)

- [ ] Write a script, management command, or fixture to load real or realistic data
- [ ] Wrap each required third-party API in its own management command, so both are integrated, not just tested standalone
- [ ] Run each command once
- [ ] Query the database directly (not through the app) to confirm rows exist
- [ ] Confirm field values look correct (types, nulls, formatting)
- [ ] Run each command a second time and confirm it creates no duplicates (idempotent)

## 4. Backend API (CRUD)

- [ ] Write serializers for each model
- [ ] Write viewsets/routes for GET, POST, PUT/PATCH, DELETE
- [ ] Register routes in urls.py
- [ ] Test every endpoint with `curl` or Postman at `http://127.0.0.1:8000` before touching any client code
- [ ] Confirm GET returns real data from step 3
- [ ] Confirm POST/PUT/DELETE actually mutate the database (re-check with step 3's query method)
- [ ] Confirm error cases return sensible status codes (400, 404, etc.) without leaking internals (no raw stack traces or SQL in the response)
- [ ] Handle nested/related resources: creating, updating, and deleting nested objects through the API, not just flat single-model CRUD
- [ ] Keep response shape consistent across endpoints (same field naming, same pagination wrapper) so clients don't need special-case parsing per endpoint
- [ ] Paginate list endpoints from the start, even with a small dataset; it's cheap now and painful to retrofit later
- [ ] Confirm PUT/DELETE are idempotent: calling one twice produces the same end state as calling it once
- [ ] Validate/sanitize input on the backend even though the frontend also validates; the API is the real gate, not the UI

## 5. Auth

Auth comes before feature endpoints because user-owned resources (votes, keywords) need a logged-in user.

- [ ] Use Django's built-in `User` and DRF token auth
- [ ] Sign-up endpoint: validates with Django's password validators, creates the user, returns a token
- [ ] Log-in endpoint: returns a token for valid credentials, 400 otherwise
- [ ] Log-out endpoint: deletes the user's token
- [ ] Confirm protected endpoints reject unauthenticated requests
- [ ] Confirm a valid token grants access and an invalid one doesn't
- [ ] Confirm authenticated ≠ authorized: a regular user's token can't hit staff-only endpoints just because it's valid
- [ ] Lock down data that ingestion owns (for DevFeed: sources, tags, articles) so only staff can write to it

## 6. User-Owned Resources & Feature Endpoints

- [ ] Full CRUD on each user-owned resource, scoped so users only see and change their own rows (for DevFeed: keywords)
- [ ] Set the owner from `request.user` on create; never trust an owner id from the request body
- [ ] Design non-CRUD endpoints as parameterized from the start (e.g., a `fields` param on search) so adding scope later doesn't require reworking the endpoint
- [ ] Build the narrowest working version first (e.g., autocomplete on tags only, a simple up/down vote counter) before expanding scope
- [ ] Confirm each endpoint composes cleanly with pagination and response-shape conventions from step 4
- [ ] Note any feature that implies a future ML/re-ranking layer (e.g., vote-driven ranking) as a stretch goal, not part of this pass

## 7. Automated Tests for the API

- [ ] Write tests for each endpoint (happy path + at least one failure case)
- [ ] Include tests for sign-up/log-in/log-out, ownership (one user can't read or change another's rows), feature endpoints, and auth-protected routes
- [ ] Assert on what the API returns (behavior), not on internal method calls, so refactoring doesn't break tests unnecessarily
- [ ] Run the test suite and confirm everything passes
- [ ] Deliberately break something (typo a field name, change a status code) and confirm a test catches it
- [ ] Fix the deliberate break, confirm tests pass again

## 8. Environment Config, CORS & Reverse Proxy

- [ ] Move every secret and setting into `.env` (`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL`, `POSTGRES_*`, `CORS_ALLOWED_ORIGINS`, API tokens), never hardcoded
- [ ] Commit a `.env.example` listing every variable with placeholder values; confirm `.env` is in `.gitignore`
- [ ] Search the git history for committed secrets; if any turn up, rotate them, don't just delete the line
- [ ] Configure `django-cors-headers` so the React dev server (a different origin) can call the API
- [ ] Plan the production layout: NGINX serves the React build and proxies `/api/` to the backend, so both share one origin
- [ ] Remember `VITE_API_URL` is baked in at `npm run build`, not read at runtime

## 9. Containerize (Docker)

- [ ] Write a Dockerfile for the backend (Gunicorn) and a multi-stage one for the frontend (Node build, then NGINX)
- [ ] Add a `.dockerignore` to each so `node_modules`, virtual environments and `.env` never end up in an image
- [ ] Write a `docker-compose.yml` with `db` (Postgres with a named volume and a real user/password), `backend` and `frontend`
- [ ] Build and run locally with Docker; confirm it behaves the same as my non-Docker local setup
- [ ] Run migrations inside the container (`docker compose exec backend python manage.py migrate`); don't assume they carry over
- [ ] Re-run the step 4–7 checks against the containerized version

## 10. React Frontend: Shell and Core Flow

- [ ] Set up the React project with Vite and Material UI (`@mui/material`, `@mui/icons-material`)
- [ ] One MUI theme (palette, typography, dark mode) instead of scattered CSS
- [ ] Add routing (React Router) and an app bar with navigation between every page
- [ ] Fetch from the API with loading and error states (TanStack Query or `useEffect`)
- [ ] Sign-up, log-in and log-out in the UI; store the token, send it on requests, handle a 401
- [ ] Share the logged-in user through Context
- [ ] Get one core flow working end to end against the real API (for DevFeed: the paginated feed)

## 11. First Deploy (Walking Skeleton)

- [ ] Set a $10 monthly AWS budget alert before launching anything
- [ ] Launch the EC2 instance; security group allows SSH from my IP only and HTTP from anywhere
- [ ] Install Docker and the Compose plugin
- [ ] Clone the repo, create `.env` from `.env.example` with production values
- [ ] `docker compose up -d --build`, then run migrations and `createsuperuser` inside the backend container
- [ ] Run the ingestion commands once on the server and confirm rows in Postgres
- [ ] Confirm the site loads from outside the instance and sign-up/log-in work on the live URL
- [ ] Ship it even if it's unfinished and ugly; production surprises (CORS, env vars, migrations) are cheaper to find now

## 12. React Feature Completion

- [ ] Build out full CRUD in the UI for each user-owned resource (list, create, edit, delete)
- [ ] Build the autocomplete search bar (debounced input, calls the endpoint from step 6)
- [ ] Build the voting UI (thumbs up/down, reflects the current vote per article)
- [ ] Manually click through every CRUD operation in the browser
- [ ] After each action, re-check the database directly to confirm nothing silently failed
- [ ] Redeploy after each feature lands, not all at the end

## 13. Production Hardening & Regression Pass

- [ ] Schedule ingestion on the server (cron calling the management commands)
- [ ] Re-run the step 4–7 checks against the deployed URL
- [ ] Click through every user flow in production, not only locally
- [ ] Confirm the database connection, migrations and env vars are correct on the server
- [ ] Set up basic logging so failures are visible after deployment
- [ ] Re-run the full automated test suite one more time before calling it done

## 14. Code Quality / Refactor Pass

- [ ] Check for N+1 query problems (looping over a queryset and hitting the DB per iteration); fix with `select_related`/`prefetch_related`
- [ ] Look for duplicated fetch/error-handling logic in the frontend that could live in one API module
- [ ] Confirm views stay thin: business logic lives in models/serializers/services, not sprawling across view functions
- [ ] Revisit any abstraction I added early: did I actually repeat this 2-3 times, or did I abstract before I needed to (YAGNI/KISS check)?
- [ ] Consistent formatting across the codebase (Black/Ruff for Python, Prettier for JS)
- [ ] Re-run the full test suite after any refactor to confirm behavior didn't change, only structure

## 15. Documentation & Presentation

- [ ] README: what the app does and the problem it solves, screenshots or a demo GIF, live link, setup steps someone can follow from `git clone`, technologies used, ERD
- [ ] Confirm the setup steps work from a fresh clone
- [ ] Record a backup demo walkthrough before presentation day
- [ ] Prepare the 5–10 minute presentation: what it does, live demo, tech stack, hardest problem debugged, what I'd do with another week
- [ ] Add the project to my LinkedIn and GitHub profile README once it's deployed

## 16. CI/CD (Optional, Exceeds Expectations)

- [ ] Set up GitHub Actions to run the backend test suite on every push/PR
- [ ] Add branch protection so merges require passing tests
- [ ] Set up continuous deployment so a merge to main triggers a deploy

## 17. Frontend E2E Tests (Optional)

- [ ] Write Playwright tests covering the core user flows (view list, create, edit, delete, search, vote)
- [ ] Include a test for the auth flow (sign up, log in, protected route redirect, log out)
- [ ] Run the suite against a real running backend, not a mock

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
