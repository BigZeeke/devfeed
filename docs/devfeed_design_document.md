# DevFeed Design Document

Oct 10, 2026 · @Steve Lopez

## Overview

DevFeed is a personalized developer news digest: it pulls stories from Hacker News, GitHub and curated RSS feeds into one database and serves them through a single API to a React web app. A command-line client on the same API is a stretch goal.

Developers follow news across many sites, each with its own format and noise level. DevFeed collects those sources in one place, lets a user filter by the languages and frameworks they care about, and learns from thumbs up/down votes which articles to rank higher.

It is my Code Platoon (Cohort Juliett) capstone project. The repository is [github.com/BigZeeke/devfeed](https://github.com/BigZeeke/devfeed).

It's built for developers who want one filtered feed instead of a handful of open tabs, including people like me who would rather read it from a terminal.

## Goals and non-goals

The MVP is scoped to the Module 9 requirements and roughly 50 hours of build time: React, DRF, PostgreSQL, Docker Compose and a live deploy on AWS EC2. Anything not needed to meet those requirements is a stretch goal.

### Goals

1. One Django REST Framework API on PostgreSQL as the single source of truth.
2. Two third-party APIs feeding the database: the Hacker News Algolia API and the GitHub Search API. The GitHub Trending scrape and RSS feeds are extra sources on top of those two.
3. Sign up, log in and log out with DRF token auth.
4. Full CRUD from the React UI on two user-owned resources: followed keywords and votes.
5. Tag filtering with server-side autocomplete.
6. A React + MUI frontend with navigation between the feed, article detail, keywords and login pages.
7. The whole stack running in Docker Compose and deployed to AWS EC2, with a first deploy in Week 23.
8. No secrets in git: settings come from `.env`, documented in a committed `.env.example`.
9. Every step checked against real Postgres, with backend tests for each endpoint.

### Out of scope for the capstone

- A custom user model; Django's built-in `auth.User` is enough.
- The plain HTML/CSS/JS checkpoint; the frontend goes straight to React to save build hours.
- Real-time features (WebSockets), payments and a native mobile app.
- A Blazor/ASP.NET client; the stack stays Python/Django plus React.

The CLI client, digests, LLM re-ranking and free-text search are stretch goals, listed at the end of this doc.

## System architecture

One Django REST Framework API sits in front of one Postgres database. The web UI goes through that API, as would the stretch-goal CLI; no client talks to the database directly.

&#91;embedded content: DevFeed architecture · 6 components\]

The old CLI fetchers became the ingestion layer. They fill the database on the backend instead of acting as a user-facing client.

## Data model

The schema spans three Django apps and Django's built-in `auth.User`; it is migrated and verified on real Postgres. The ERD is in `docs/devfeed_erd.png`, drawn from `docs/devfeed_schema_drawdb_full.sql`: the live Postgres schema plus the planned `authtoken_token` table from Step 5. The older design-time SQL is in `docs/devfeed_schema.sql`.

| App | Model | Purpose | Key relationships and constraints |
| --- | --- | --- | --- |
| articles | Source | Where an article came from (Hacker News, GitHub, Real Python, InfoQ) | One Source has many Articles |
| articles | Tag | A language, framework or topic label (React, Django) | Plain ManyToManyField with Article, no extra columns |
| articles | Article | One story or repository in the feed | FK to Source; M2M to Tag; `url` is unique (the dedup key, enforced in Postgres); `published_at`; `raw_score` from the source; `is_read` is a shared flag, not per user, unused by the MVP |
| articles | Vote | A user's thumbs up/down on an article | FK to User and Article; unique (user, article); nullable `direction`; `created_at`, `updated_at` |
| digests | Digest | A generated digest of ranked articles | No link to a user (shared, not per user); articles through DigestItem |
| digests | DigestItem | One article's place in a digest | Through-model with a `rank` field |
| user\_profiles | UserKeyword | A keyword a user follows | FK to User |

### Vote design

- One row per user and article, enforced by a unique constraint, so a vote is updated rather than duplicated.
- `direction` is `up`, `down` or `null`. Null means the user took the vote back; the row stays.
- A vote switches directly from up to down in one action; there is no forced neutral step in between.

### Other decisions

- Django's built-in `auth.User` instead of a custom user model.
- Category filtering reuses the `Tag` model; no separate category field.

## Ingestion layer

Ingestion is a backend-only layer: fetchers pull from each source and Django management commands write the results to Postgres. The Hacker News Algolia API and the GitHub Search API are the two third-party APIs that meet the project requirement. Hacker News is wired in; the GitHub and RSS fetchers are built and tested but not yet wrapped in commands.

| Source | Method | Notes | Status |
| --- | --- | --- | --- |
| Hacker News | Algolia HN Search API, `search_by_date`, `tags=story` | Ask-HN/text posts with no external URL fall back to the HN discussion page URL; `raw_score` from HN points | Fetcher + `ingest_hacker_news` command done, verified on Postgres |
| GitHub Trending | Scrapes `github.com/trending` HTML (`article.Box-row` elements); no official API exists | Feeds the homepage trending banner, not the main feed | Fetcher built and tested |
| GitHub Search API | `api.github.com/search/repositories` | One of the two required APIs, and the fallback when the scrape breaks; optional `GITHUB_PERSONAL_ACCESS_TOKEN` raises the rate limit | Fetcher built and tested |
| RSS | `feedparser` against Real Python (`realpython.com/atom.xml`) and InfoQ (`feed.infoq.com`) | Easy to add more feeds | Fetcher built, verified via Postman |

### Write path

Every source follows the same pattern as the Hacker News command:

```text
for each item returned by the fetcher:
    article, was_created = Article.objects.get_or_create(url=item.url, defaults={...})
    if was_created:
        set source, title, published_at (parse_datetime), raw_score
        attach tags (empty for HN for now)
        count as created
    else:
        count as skipped
print created and skipped counts
```

Dedup relies on the unique constraint on `Article.url`. A second HN run returned 0 created and 20 skipped, confirming the command is idempotent.

Still to do: an `ingest_github` command using the same pattern. It's part of the MVP because it's one of the two required APIs. `ingest_rss` follows after. A repo's language would make a good first tag.

## API design

The articles app's CRUD API is live under `/api/`; Step 5 adds filtering, autocomplete, voting and token login on top of it. Planned paths below are proposals and may change during the build.

### Built in Step 4

| Method | Path | Purpose |
| --- | --- | --- |
| GET, POST | `/api/articles/` | List articles (paginated, 20 per page); create an article with `tag_labels` |
| GET, PUT, PATCH, DELETE | `/api/articles/{id}/` | Article detail and changes |
| GET, POST | `/api/sources/` | List or create sources |
| GET, PUT, PATCH, DELETE | `/api/sources/{id}/` | Source detail and changes |
| GET, POST | `/api/tags/` | List or create tags |
| GET, PUT, PATCH, DELETE | `/api/tags/{id}/` | Tag detail and changes |

Implementation: `ModelViewSet` for each model with `select_related`/`prefetch_related`, registered on a `DefaultRouter`. The article serializer nests read-only `tags` and accepts a write-only `tag_labels` list that runs `get_or_create` on `Tag`.

### Planned for Step 5 and later

| Method | Path | Purpose | Auth |
| --- | --- | --- | --- |
| POST | `/api/auth/register/` | Sign up with username, email and password; returns a token | Public |
| POST | `/api/auth/token/` | Log in; exchange username and password for a token | Public |
| POST | `/api/auth/logout/` | Log out; deletes the user's token | Token |
| GET, POST | `/api/keywords/` | List or add my followed keywords | Token |
| GET, PUT, PATCH, DELETE | `/api/keywords/{id}/` | Read, edit or delete one of my keywords | Token, owner only |
| POST | `/api/articles/{id}/vote/` | Body `{"direction": "up"}` or `"down"`; creates or switches the vote | Token |
| DELETE | `/api/articles/{id}/vote/` | Removes the vote (sets `direction` to null) | Token |
| GET | `/api/articles/?tag=django&source=hacker-news` | Filter the feed by tag and source | Public |
| GET | `/api/tags/autocomplete/?prefix=dja` | Tag suggestions for the search bar | Public |
| GET | `/api/trending/` | GitHub Trending items for the homepage banner | Public |
| GET | `/api/digests/` | My digest (stretch) | Token |

Once sign-up exists, the Step 4 CRUD on sources, tags and articles becomes read-only for regular users. Writes there need staff permission, since ingestion owns that data.

All list endpoints keep `PageNumberPagination` with `PAGE_SIZE` 20.

## Feature designs

Three features build on the articles API: tag search and filtering, voting, and a GitHub Trending banner. All three reuse existing models.

### Tag search and category filtering

The search bar suggests tags as the user types. Matching happens on the server so every client gets the same results. Categories like React or Django are just tags, so filtering by category and filtering by tag are the same query. Title and source matching can be added once the tag version works.

```text
GET /api/tags/autocomplete/?prefix=<typed text>
    if prefix is shorter than 2 characters: return empty list
    matching_tags = Tag where label starts with prefix (case-insensitive)
    order matching_tags by label
    return first 10 labels

GET /api/articles/?tag=<label>&source=<name>
    articles = all articles, newest first
    if tag given: keep articles that have that tag
    if source given: keep articles from that source
    return one page of 20
```

### Voting

A logged-in user can vote an article up or down, switch the vote, or take it back. The first version adjusts a score used for sorting. LLM re-ranking based on vote history comes later.

```text
POST /api/articles/<id>/vote/   body: direction = up | down
    require login
    vote = Vote.get_or_create(user, article)
    vote.direction = direction      (up to down works in one call)
    save vote
    return article id, my vote, current score

DELETE /api/articles/<id>/vote/
    require login
    if vote exists: vote.direction = null, save
    return article id, current score

current score = raw_score + (up votes) - (down votes)
```

The score formula is a starting point. I'll tune it once there is real vote data.

### GitHub Trending banner

Trending repositories show in a strip at the top of the homepage, separate from the main feed. The fetcher scrapes github.com/trending and falls back to the GitHub Search API if the scrape fails. How trending items are stored (their own Source in the Article table, or a separate table) is still open.

### Followed keywords

A logged-in user keeps a list of keywords (for example `django`, `postgres`, `rust`). This is the main user-facing CRUD resource, and it shapes a "My feed" view. The `UserKeyword` model already exists; it needs a serializer, a viewset and a page.

```text
/api/keywords/   (KeywordViewSet, login required)
    queryset = UserKeyword where user = request.user     (users only see their own)
    on create: set user = request.user; reject a duplicate keyword for the same user
    list, retrieve, update, partial_update, destroy: standard ModelViewSet

GET /api/articles/?mine=true   (login required)
    keywords = my followed keywords
    articles = articles whose title contains any keyword, or that have a tag matching one
    return one page of 20, newest first
```

The keywords page in React lists keywords as MUI `Chip`s with delete buttons, has a `TextField` to add one, and allows renaming a keyword inline. That covers create, read, update and delete in the UI.

### Sign up, log in, log out

Auth uses Django's built-in `User` and DRF's `TokenAuthentication`. The same token works for the React app and, later, the CLI.

```text
POST /api/auth/register/   body: username, email, password
    validate with Django's password validators
    create the user, create a token
    return the token and username

POST /api/auth/token/      body: username, password
    return the token if the credentials match, else 400

POST /api/auth/logout/     (login required)
    delete request.user's token
    return 204

React
    AuthContext keeps the token in memory and localStorage
    the app bar shows Log in / Sign up, or the username and Log out
    Log out calls the logout endpoint, then clears the token
```

## CLI client

The CLI is a stretch goal: it isn't required, and the 50-hour budget goes to the MVP first. The design is kept here so it's ready if time allows. It's a thin client over the same REST API the web app uses, runs one command and exits, and has no database access of its own.

| Command | What it does | API call |
| --- | --- | --- |
| `devfeed feed [--tag T] [--source S] [--limit N]` | List the feed, optionally filtered | `GET /api/articles/` |
| `devfeed show <id> [--open]` | Show one article; `--open` also launches it in the browser | `GET /api/articles/<id>/` |
| `devfeed open <id>` | Open the article URL with Python's `webbrowser.open()` | `GET /api/articles/<id>/` |
| `devfeed login` | Ask for username and password, store the token locally | `POST /api/auth/token/` |
| `devfeed vote <id> up\|down` | Vote on an article | `POST /api/articles/<id>/vote/` |
| `devfeed unvote <id>` | Remove a vote | `DELETE /api/articles/<id>/vote/` |
| `devfeed digest` (later) | Show my digest | `GET /api/digests/` |
| `devfeed keywords add\|list` (later) | Manage followed keywords | `/api/keywords/` |

`feed --tag` is how filtering works in the CLI. I'm keeping the name `search` free for a later free-text search over titles.

The token from `login` is saved in a local config file and sent as an `Authorization` header on calls that need it. The API base URL defaults to `http://127.0.0.1:8000`.

## Web frontend

The web client is a React app built with Vite and Material UI (MUI). MUI supplies the layout, inputs, cards, dialogs and theming, so most screens are put together from its components instead of hand-written CSS. The frontend goes straight to React; there's no separate plain HTML/CSS/JS version.

### Stack

| Layer | Choice | Reason |
| --- | --- | --- |
| Build tool | Vite | Fast dev server; proxies `/api` to `http://127.0.0.1:8000` so there are no CORS issues in development |
| Components | `@mui/material`, `@mui/icons-material` (with `@emotion/react`, `@emotion/styled`) | Ready-made, accessible components that cover every screen in DevFeed |
| Styling | One MUI theme plus the `sx` prop | Replaces CSS Modules; colors, type and dark mode live in one place |
| Routing | React Router | Home, article detail, login, digest |
| Server data | TanStack Query | Caching, pagination and refetching after a vote |
| HTTP | Small `fetch` wrapper in `api/client.js` | Adds the token header and the base URL in one spot |
| Auth state | React context holding the token | Shared by the app bar, voting and login |

MUI's current major version is v9 (9.2.0 per its release tracker as of October 2026); I'll pin whatever is current when I install.

### Component map

| DevFeed feature | MUI components |
| --- | --- |
| App shell and navigation | `ThemeProvider`, `CssBaseline`, `AppBar`, `Toolbar`, `Container`; app bar links to Feed, My feed and Keywords; `Drawer` menu on small screens |
| Trending banner | Horizontal `Stack` of `Card`s, each with a `Link` to the repo |
| Article feed | `Grid` of `Card`s: `CardContent`, `Typography`, `Chip` per tag, `CardActions` |
| Voting | `ToggleButtonGroup` with `ThumbUp` and `ThumbDown` icons; clicking the active button removes the vote |
| Tag search | `Autocomplete` fed by `/api/tags/autocomplete/`, debounced while typing |
| Source filter | `Select` in the toolbar |
| Paging | `Pagination` tied to the API's page number |
| Article detail | Its own route with a `Button` and `OpenInNew` icon to the original |
| Log in and sign up | `Dialog` with `Tabs` for the two forms, `TextField`s and a `Button` |
| Keywords page | `Chip`s with delete buttons, `TextField` plus `Button` to add, inline edit on click |
| Loading and errors | `Skeleton` cards while loading; `Snackbar` with an `Alert` on failure |
| Dark mode | `IconButton` in the app bar switching the theme's palette mode |

### Project structure

```text
devfeed_web/
  vite.config.js            proxy /api -> http://127.0.0.1:8000
  src/
    main.jsx                ThemeProvider, QueryClientProvider, Router
    theme.js                palette, typography, light and dark modes
    api/
      client.js             fetch wrapper: base URL, token header, errors
      articles.js           getArticles, getArticle, voteOnArticle, removeVote
      tags.js               getTagSuggestions
      keywords.js           getKeywords, addKeyword, renameKeyword, deleteKeyword
      auth.js               register, requestToken, logout
    context/
      AuthContext.jsx       token, login, logout
    components/
      AppShell.jsx          AppBar, search, source filter, theme toggle
      TrendingBanner.jsx
      ArticleCard.jsx
      VoteButtons.jsx
      TagSearch.jsx
      AuthDialog.jsx        log in and sign up tabs
    pages/
      FeedPage.jsx
      ArticleDetailPage.jsx
      KeywordsPage.jsx
      DigestPage.jsx        later
```

### Data flow

The feed page reads its filters from the URL, so a filtered view can be bookmarked or shared.

```text
FeedPage
    read tag, source, page from the URL query string
    articlesQuery = useQuery(['articles', tag, source, page], getArticles)
    if loading: show Skeleton cards
    if error: show Snackbar with Alert
    render TrendingBanner, then a Grid of ArticleCard, then Pagination

TagSearch (Autocomplete)
    on input change: wait 250 ms, then getTagSuggestions(typed text)
    on select: set tag in the URL, reset page to 1

VoteButtons
    if not logged in: open AuthDialog
    on click: update the card's vote and score right away
              send voteOnArticle or removeVote
              on failure: put the old vote back, show Alert
              on success: refetch the articles query
```

MUI covers what react-chat-elements was meant to provide, so that library is no longer part of the plan.

### Wireframes

These four pages are the wireframes for the proposal. They cover every MVP flow: browse and filter, read and vote, sign up and log in, and manage keywords.

&#91;embedded content: DevFeed wireframes · 4 pages\]

The app bar is the same on every page; it shows Log in when signed out and Log out when signed in.

## Configuration and local environment

Settings come from a `.env` file at the repo root, which stays out of git.

| Variable | Local | Production (EC2) | Used for |
| --- | --- | --- | --- |
| `SECRET_KEY` | Dev value in `.env` | Long random value, only on the server | Django signing |
| `DEBUG` | `True` | `False` | Error pages and static handling |
| `ALLOWED_HOSTS` | `127.0.0.1,localhost` | EC2 public address or domain | Host header check |
| `DATABASE_URL` | `postgres://veteran@localhost:5432/devfeed` (peer auth, no password) | `postgres://devfeed:<password>@db:5432/devfeed` | Postgres connection via `dj-database-url` |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Not needed | Read by the Postgres container on first start | Creating the database and its user |
| `CORS_ALLOWED_ORIGINS` | `http://127.0.0.1:5173` | The site's own origin | `django-cors-headers` |
| `VITE_API_URL` | `/api` (Vite proxy) | `/api` (nginx proxy) | API base URL; baked into the bundle at `npm run build` |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | Optional | Optional | Higher GitHub Search API rate limit |

Every variable is listed in the committed `.env.example` with placeholder values, and `.env` stays in `.gitignore`. Peer auth works on my laptop but not between containers, so the containerized database always gets a user and password.

Other notes:

- Auth uses Django's built-in `auth.User` plus DRF token auth for the web client (and the CLI, if built).
- Local API testing always goes to `http://127.0.0.1:8000`, never `localhost`. On my machine `localhost` resolves to IPv6, where Docker Desktop's backend also listens, which hid the real DevFeed server during Step 4.
- One virtual environment at the repo root serves `devfeed_api` and the CLI if it gets built; the web client has its own Node dependencies.

## Deployment

DevFeed runs as three Docker Compose services on one AWS EC2 instance, with the first deploy in Week 23 even if the app is half built. The Week 21 Dockerize + Deploy lesson is the playbook; where it differs from this plan, the lesson wins.

### Compose services

| Service | Built from | Notes |
| --- | --- | --- |
| `db` | Official `postgres` image, pinned to a major version | Named volume `postgres_data` so data survives restarts; reads `POSTGRES_*` from `.env`; no public port |
| `backend` | `devfeed_api/Dockerfile` | Runs Gunicorn on port 8000; `env_file: .env`; depends on `db` |
| `frontend` | `devfeed_web/Dockerfile`, multi-stage | Node stage runs `npm run build`; nginx stage serves the bundle on port 80 and proxies `/api/` to `backend:8000` |

Serving the React bundle and the API from the same origin keeps CORS simple in production. Each project folder gets a `.dockerignore` so `node_modules`, virtual environments and `.env` never end up in an image.

### Production settings

- `DEBUG=False`, `ALLOWED_HOSTS` set to the EC2 address, `SECRET_KEY` only on the server.
- `gunicorn` and `django-cors-headers` added to `requirements.txt`.
- `collectstatic` run in the backend image so the Django admin has its CSS.
- Write access on sources, tags and articles limited to staff.

### Deploy steps

1. Set a $10 monthly AWS budget alert before launching anything.
2. Launch an EC2 instance; the security group allows port 22 from my IP only and port 80 from anywhere.
3. Install Docker and the Compose plugin on the instance.
4. Clone the repo and create `.env` from `.env.example` with production values.
5. Build and start: `docker compose up -d --build`.
6. Apply migrations: `docker compose exec backend python manage.py migrate`.
7. Create an admin user: `docker compose exec backend python manage.py createsuperuser`.
8. Run each ingest command once and confirm rows in Postgres with `psql` inside the `db` container.
9. In a browser: sign up, log in, add a keyword, vote, log out.

### Scheduled ingestion

A cron entry on the EC2 host runs `docker compose exec -T backend python manage.py ingest_hacker_news` and `ingest_github` a few times a day. That keeps the feed fresh while staying well inside both APIs' rate limits.

### Optional extras

- HTTPS with free auto-renewing TLS (Week 21 Day 4 optional section).
- A GitHub Actions workflow that runs the backend tests on every PR.

## Testing and verification

No step counts as done until I've checked it against real Postgres. A clean command output or API response is not enough on its own.

1. Verify each layer against the layer below it before moving up. Endpoints are only built for models that already have real data in the database.
2. Check writes in the database directly (a `manage.py shell` query or `psql`), not only in the API response. Step 4's `tag_labels` POST was confirmed this way.
3. Run every ingestion command twice. The second run must create nothing new.
4. Hit the API with curl or Postman at `http://127.0.0.1:8000`.
5. Add Django/DRF tests for each endpoint as it's built: filtering, autocomplete limits, vote create/switch/remove, register/login/logout, keyword ownership (one user can't read or change another's keywords), and auth required on protected endpoints.
6. Check every web UI flow in production after each deploy, not only on my laptop.

## Build plan and status

Steps 1 through 4 of my build checklist are done, which puts the backend ahead of the suggested pacing. The plan below maps the rest onto the Weeks 22–24 schedule; only the proposal and presentation dates are fixed. Each step stays a GitHub Issue on the project board.

| When | Work | Status |
| --- | --- | --- |
| Before Week 22 | Data model, HN ingestion, CRUD API for sources, tags and articles (checklist Steps 1–4) | Done |
| Week 22 Day 2 | Proposal: MVP, ERD, wireframes and the two APIs from this doc | Fixed date |
| Week 22 | `ingest_github` command; register, login and logout endpoints; keywords API; voting, filtering and autocomplete endpoints; backend tests | Next |
| Week 23 Days 1–2 | Dockerfiles and Compose running locally; React + MUI shell, auth dialog, feed page | Planned |
| Week 23 Day 3 | First deploy to EC2, even if unfinished | Planned |
| Week 23 Day 4 | Keywords page, voting UI, article detail; redeploy | Planned |
| Week 24 Days 1–2 | Styling, production bug fixes, redeploy | Planned |
| Week 24 Day 3 | Final redeploy; README, screenshots, recorded demo backup | Planned |
| Week 24 Day 4 | Presentation | Fixed date |
| If time allows | Stretch goals, in the order listed below | Stretch |

## README, git workflow and presentation

Documentation, git history and the presentation are 35% of the grade together, so each has a plan instead of being left for the last day.

### README sections

1. What DevFeed is and the problem it solves, in two or three sentences a recruiter can read in under a minute.
2. Screenshots of the feed, keywords page and sign-up, plus a short demo GIF.
3. Live link to the EC2 deploy.
4. Setup: clone, copy `.env.example` to `.env`, `docker compose up --build`, run migrations, run the ingest commands.
5. Technologies: React, MUI, Vite, Django REST Framework, PostgreSQL, Docker Compose, nginx, AWS EC2, Hacker News Algolia API, GitHub Search API.
6. ERD: `docs/devfeed_erd.png` embedded, with a link to `docs/devfeed_schema.sql`.
7. How AI tools were used in the build.

### Git workflow

- Small commits with clear messages throughout all three weeks.
- One branch and pull request per GitHub Issue, merged into `main`.
- Each PR description says whether any code was materially AI-generated, per the course rules.
- Every line shipped is one I can walk through in code review.

### Presentation (5–10 minutes)

| Section | Content |
| --- | --- |
| What it does | One feed of developer news from Hacker News and GitHub, filtered by the tags and keywords I follow |
| Live demo | Sign up, filter by tag, vote, add and remove a keyword, log out; recorded backup ready |
| Tech stack | The architecture diagram from this doc |
| Hardest problem | Step 4: `localhost` resolving to IPv6, where Docker Desktop was also listening, hid the real server; a stray process also held port 8000. Fixed by always testing at `127.0.0.1` |
| Another week | CLI client on the same API, then digests built from followed keywords |

## Risks, open questions and stretch goals

### Risks

| Risk | Impact | Plan |
| --- | --- | --- |
| GitHub changes the trending page HTML | Trending banner goes empty | Fall back to the GitHub Search API |
| Source API rate limits | Ingestion runs fail or return less | Optional GitHub token; keep runs infrequent |
| HN articles have no tags | Tag filtering misses most of the feed | Decide on a tagging approach before Step 5 ships |
| Scope creep from stretch features | Core features slip | Stretch goals wait until the MVP is deployed and working |

### Open questions

- Does ingestion through management commands count as integrating the two APIs, or should one be called during a user request? To confirm with the instructor at the proposal.
- How do HN articles get tags: keyword matching on titles, or left untagged?
- Do trending repositories go in the Article table under their own Source, or in a separate table?
- What weight should votes carry against `raw_score`?

### Stretch goals

1. CLI client on the same API (design in the CLI section).
2. Digests built from followed keywords. This needs a user ID column on Digest first, since today's table has none.
3. `ingest_rss` command for Real Python and InfoQ.
4. Free-text search over titles and sources.
5. LLM re-ranking of the feed from each user's vote history.
