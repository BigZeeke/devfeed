# DevFeed Presentation Outline

My plan for the Code Platoon Module 9 presentation on Saturday, November 14, 2026: about 10 minutes plus an optional minute on my GitHub process, built around a live demo that starts in the CLI, moves to the web app and comes back, to show both clients using the same API. The prep steps are in [`demo_prep_checklist.md`](demo_prep_checklist.md).

## 1. What DevFeed is (about 1 minute)

1. The problem: developer news is spread across Hacker News and GitHub. DevFeed puts it in one feed where I can save articles with notes and follow the keywords I care about.
2. Two clients, one API: a React web app and a `devfeed` command-line client, both talking to the same Django REST Framework API. The live demo proves it.

## 2. Tech stack (about 1.5 minutes)

1. Frontend: React 19 and Material UI on Vite.
2. CLI: Python with `argparse` and `requests`, no extra dependencies.
3. Backend: Django REST Framework with token authentication, on PostgreSQL 18.
4. Third-party APIs: the Hacker News Algolia API and the GitHub Search API, loaded by management commands.
5. Containers and hosting: Docker Compose with three services (`db`, `backend`, `frontend`) on one AWS EC2 instance; NGINX serves the React build and proxies `/api/` to Django.
6. Show the ERD (`docs/devfeed_erd.png`).

## 3. Design decisions (about 1.5 minutes)

1. **One API for every client.** Neither client touches the database. I built the CLI as new files only, with no backend changes, which is the proof that the API was designed well enough to serve a second client.
2. **Same origin through NGINX.** The web app and the API share one address in production, so no CORS is needed there.
3. **Owner-scoped CRUD.** Bookmarks and keywords belong to the logged-in user; another user's row returns 404 instead of 403, so the API doesn't reveal that it exists.
4. **Votes as one row per user and article** with a nullable direction: switching or taking back a vote updates the row instead of adding rows.
5. **Idempotent ingestion.** Articles are deduplicated on their URL, so rerunning the ingestion commands creates no duplicates.
6. **CLI choices.** Log-ins are stored per server, so local and live sessions exist side by side; anything that removes data asks `[y/N]` first; exit codes follow Unix conventions (0, 1, and 2 for a mistyped command).

## 4. Live demo (about 5 minutes)

The demo walks through full CRUD on bookmarks, moving between the two clients so every step shows the same API and the same data.

1. `devfeed --help`: every command at a glance. Then `devfeed save --help` to show how a command documents its own arguments.
2. **Create, in the CLI:**
   1. `devfeed feed`, and pick an article.
   2. `devfeed save <id> --note "Saved from the terminal"`
   3. `devfeed keywords follow django --weight 2`
   4. Optionally `devfeed vote <id> up`: voting is in the CLI but not in the web app yet.
3. **Read, in the web app:** `devfeed web saved` opens the browser on the Saved page, showing the bookmark with its note. Then **Keywords** in the app bar shows `django` with weight 2.
4. **Update, in the web app:** edit the note and tick **Read**.
5. **Read again, in the CLI:** `devfeed saved` shows the new note and `yes` under READ.
6. **Delete, in the web app:** back on the Saved page, **Remove** the bookmark and confirm.
7. **Read again, in the CLI:** `devfeed saved` no longer lists it. Same API, same data, two clients.

## 5. Project process on GitHub (optional, about 1 minute)

Skip this section if the talk is already past 9 minutes. The tabs are opened beforehand (see the prep checklist), so this is clicking, not typing.

1. **Repo layout:** `devfeed_api/`, `frontend/`, `cli/` and `docs/`: the API and its two clients in their own folders, plus `docker-compose.yml`.
2. **One pull request:** PR #72 (the CLI): what changed, how I verified it, known limitations, my AI disclosure, and six small commits, one per command group.
3. **Commit history on `main`:** descriptive subjects, each body listing what was verified and ending in `Refs #<issue>`.
4. **Issues:** every PR closed its issue; the open ones (#10, #13, #17) match the next phase and what I'd do with another week.

## 6. Hardest problem I debugged (about 30 seconds)

Pick one:

1. The live site didn't load from outside the server: the frontend container was published only on `127.0.0.1`. Fixed by making the host binding configurable (PR #60).
2. A token check in the browser failed on the live site because browsers block `crypto.subtle` on plain HTTP.
3. A restored file was correct, but Python kept running the broken version from its bytecode cache, because the file's size and timestamp matched the broken one. Confirmed with output before fixing.

## 7. Next phase and close (about 30 seconds)

1. The five approved-proposal features planned next, in order: GitHub Trending banner, "My feed", voting UI, article detail page, tag filtering with autocomplete.
2. With another week: HTTPS with a domain, scheduled ingestion, and CI running the tests on every pull request.
