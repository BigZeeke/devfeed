# Full-Stack Web App Build Checklist

My repeatable order for building and testing a full-stack app: build from the data outward, and don't move to the next layer until the current one is verified — not just written.

## 1. ERD (Entity-Relationship Diagram)
- [ ] Diagram entities, attributes, and relationships in drawdb.app (cardinality: one-to-many, many-to-many, etc.)
- [ ] Justify normalization decisions (e.g., why a join table exists instead of a flat text field)
- [ ] Mark primary keys, foreign keys, and any indexes worth adding upfront — especially fields I'll filter, sort, or search on
- [ ] Export/save the ERD as a real deliverable — not just sketched and discarded
- [ ] Design nested/related resources here too (e.g., a Class↔Student many-to-many, a Grade join model) before writing any code

## 2. Data Model
- [ ] Translate the ERD into models (fields, types, relationships)
- [ ] Run migrations
- [ ] Open a shell and manually create/query one row per model
- [ ] Confirm relationships (ForeignKey, ManyToMany) work as expected in the shell
- [ ] Cross-check the migration output (`python manage.py sqlmigrate`, or inspect the schema directly) against the ERD to confirm what got built matches what I designed

## 3. Data Population (Ingestion or Seed Data)
- [ ] Write a script, management command, or fixture to load real or realistic data
- [ ] Run it once
- [ ] Query the database directly (not through the app) to confirm rows exist
- [ ] Confirm field values look correct (types, nulls, formatting)

## 4. Backend API (CRUD)
- [ ] Write serializers for each model
- [ ] Write viewsets/routes for GET, POST, PUT/PATCH, DELETE
- [ ] Register routes in urls.py
- [ ] Test every endpoint with `curl` or Postman before touching any client code
- [ ] Confirm GET returns real data from step 3
- [ ] Confirm POST/PUT/DELETE actually mutate the database (re-check with step 3's query method)
- [ ] Confirm error cases return sensible status codes (400, 404, etc.) without leaking internals (no raw stack traces or SQL in the response)
- [ ] Handle nested/related resources: creating, updating, and deleting nested objects through the API, not just flat single-model CRUD
- [ ] Keep response shape consistent across endpoints (same field naming, same pagination wrapper) so clients don't need special-case parsing per endpoint
- [ ] Paginate list endpoints from the start, even with a small dataset — cheap now, painful to retrofit later
- [ ] Confirm PUT/DELETE are idempotent — calling one twice produces the same end state as calling it once
- [ ] Validate/sanitize input on the backend even though the frontend also validates — the API is the real gate, not the UI

## 5. Feature-Specific Endpoints (Search, Voting/Scoring, etc.)
- [ ] Design non-CRUD endpoints as field-aware/parameterized from the start (e.g., a `fields` param on search) so adding scope later doesn't require reworking the endpoint
- [ ] Build the narrowest working version first (e.g., search against one field, or a simple upvote/downvote counter) before expanding scope
- [ ] Confirm the endpoint composes cleanly with pagination and response-shape conventions from step 4
- [ ] Note any feature that implies a future ML/re-ranking layer (e.g., vote-driven filtering) as a stretch goal, not part of this pass

## 6. Auth
- [ ] Add Django auth (users, permissions) to the API
- [ ] Add token auth for API clients
- [ ] Confirm protected endpoints reject unauthenticated requests
- [ ] Confirm a valid token grants access, an invalid/expired one doesn't
- [ ] Confirm authenticated ≠ authorized — a regular user's token can't hit admin-only endpoints just because it's valid

## 7. Automated Tests for the API
- [ ] Write tests for each endpoint (happy path + at least one failure case)
- [ ] Include tests for nested resources, feature-specific endpoints, and auth-protected routes
- [ ] Assert on what the API returns (behavior), not on internal method calls — so refactoring doesn't break tests unnecessarily
- [ ] Run the test suite and confirm everything passes
- [ ] Deliberately break something (typo a field name, change a status code) and confirm a test catches it
- [ ] Fix the deliberate break, confirm tests pass again

## 8. First Client, End-to-End
- [ ] Choose the simpler client to build first (e.g., CLI before UI)
- [ ] Build it against the real, running API — not mocked data
- [ ] Confirm what it displays matches what's actually in the database
- [ ] Handle at least one error case gracefully (API down, empty result, bad input)

## 9. Raw HTML/CSS/JS Checkpoint
- [ ] Build a single plain HTML page with a `fetch()` call to the API
- [ ] Confirm I can GET data and render it in the DOM with no framework involved
- [ ] Confirm I can POST/PUT/DELETE from a plain JS form or button before adding React
- [ ] Style the page with plain CSS — no build tools yet
- [ ] Treat this as proof the API itself works from a browser, isolated from any framework complexity

## 10. React Frontend
- [ ] Set up the React project (Vite or Create React App)
- [ ] Recreate the same fetch/render logic from step 9 as a component (props, state, conditional rendering)
- [ ] Add routing (React Router) if the app has more than one view
- [ ] Fetch from the API with useEffect, including loading and error states
- [ ] Handle token auth on the frontend (store/send the token, redirect on 401)
- [ ] Add Context API if state needs to be shared across components (e.g., the logged-in user)
- [ ] Build the autocomplete search bar (debounced input, calls the search endpoint from step 5)
- [ ] Build the voting UI (thumbs up/down, reflects the current vote state per article)
- [ ] Build out full CRUD in the UI (list, create, edit, delete)
- [ ] Manually click through every CRUD operation in the browser
- [ ] After each action, re-check the database directly to confirm nothing silently failed

## 11. Frontend Testing (Playwright E2E)
- [ ] Write end-to-end tests covering the core user flows (view list, create, edit, delete, search, vote)
- [ ] Include a test for the auth flow (login, protected route redirect)
- [ ] Run the suite and confirm it passes against a real running backend, not a mock

## 12. Integration / Regression Pass
- [ ] Make a change through Client 1 (e.g., edit a record via the CLI)
- [ ] Confirm that change appears correctly in Client 2 (e.g., the React UI)
- [ ] Repeat in the opposite direction
- [ ] Re-run the full automated test suite (API + Playwright) one more time before calling it done

## 13. Environment Config, CORS & Reverse Proxy
- [ ] Move secrets/config into environment variables (`.env`), never hardcoded
- [ ] Configure CORS on the Django API so the React frontend (on a different origin) can call it
- [ ] Set up NGINX as a reverse proxy in front of the app(s) if serving API + frontend together
- [ ] Confirm the frontend can reach the API through the proxy exactly as it will in production

## 14. Code Quality / Refactor Pass
- [ ] Check for N+1 query problems (looping over a queryset and hitting the DB per iteration) — fix with `select_related`/`prefetch_related`
- [ ] Look for logic duplicated across the CLI and React clients (fetch/error-handling patterns) that could be shared or at least kept consistent
- [ ] Confirm views stay thin — business logic lives in models/serializers/services, not sprawling across view functions
- [ ] Revisit any abstraction I added early — did I actually repeat this 2-3 times, or did I abstract before I needed to (YAGNI/KISS check)?
- [ ] Re-run the full test suite after any refactor to confirm behavior didn't change, only structure

## 15. Containerize (Docker)
- [ ] Write a Dockerfile for the backend and a separate one for the React frontend
- [ ] Write a `docker-compose.yml` covering app + database (+ any other services, e.g. Redis, NGINX)
- [ ] Build and run locally with Docker — confirm it behaves the same as my non-Docker local setup
- [ ] Confirm migrations run correctly inside the container (don't assume they carry over from local)
- [ ] Re-run steps 4–12's manual/automated checks against the containerized version

## 16. CI/CD
- [ ] Set up GitHub Actions to run the test suite (API + Playwright) on every push/PR
- [ ] Add branch protection so merges require passing tests
- [ ] Set up continuous deployment so a merge to main triggers a deploy

## 17. Cloud Deployment (e.g., AWS/EC2)
- [ ] Provision the environment (EC2 instance, RDS/managed DB, security groups/firewall rules)
- [ ] Deploy the containerized app(s) to the environment
- [ ] Confirm the database connection works from the deployed app (not just locally)
- [ ] Confirm the API is reachable from outside the instance (correct ports open, no firewall block)
- [ ] Re-run the same CRUD and auth checks from steps 4–6, now against the deployed URL
- [ ] Confirm both clients (CLI and React UI) can reach the deployed API, not just localhost
- [ ] Set up basic logging/monitoring so failures are visible after deployment
- [ ] Document the deployment steps somewhere repeatable (a README or a script) — not just memory

## The Rules to Remember
1. **Verify against the layer below.** At every step, I check against the database, not just "the screen looked right" — and I don't start the next layer until the current one is confirmed working. This holds through deployment: a container isn't "done" until I've verified it behaves the same as my tested local version, and a deployment isn't "done" until I've re-run my CRUD checks against the live URL.
2. **Watch for DRY, efficiency, and scope creep as I go — not just at the end.** Before marking any step done, I ask: did I duplicate logic I already wrote, is this the right query/algorithm for the data size, and did I build only what this step actually needs? Step 14 exists as a dedicated pass specifically for what's hard to catch in the moment (N+1 queries, cross-client duplication) — not as a substitute for catching the obvious stuff early.

## Optional Next Steps (once the above is solid)
- **GraphQL**: a single endpoint where the client asks for exactly the fields it wants, instead of many fixed-shape REST endpoints. Worth exploring as a stretch add-on once REST is solid.
- **AI/LLM integration**: embeddings/vector search, RAG (retrieval-augmented generation), and AI API integration into a Django backend — including using vote data to train a preference/re-ranking model instead of simple score-based filtering. A separate skill track from core full-stack CRUD — worth its own pass once the base app is deployed and stable.
