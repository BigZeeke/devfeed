# DevFeed Demo Prep Checklist

Step-by-step preparation for the presentation on Saturday, November 14, 2026, and the live demo in [`presentation_outline.md`](presentation_outline.md). The demo runs against the live site at `44.248.236.123` as `live_test_user`.

Commands run in the terminal from the repo root (prompt `devfeed on  main`) with the venv active, unless a step says otherwise. Commands contain no `http://`, so they paste cleanly into zsh.

## Before the day (by Friday, November 13)

### 1. Check the repo and the server

1. Confirm `main` is current:

   ```zsh
   git fetch --prune && git --no-pager log --oneline -3 origin/main && git status --short --branch
   ```

   Expected: `main...origin/main` with no changes.

2. Confirm the three containers are running on the server:

   ```zsh
   ssh -i ~/.ssh/devfeed_ec2 ubuntu@44.248.236.123 'cd ~/devfeed && docker compose ps'
   ```

   Expected: three rows (`backend`, `db`, `frontend`), each with a STATUS starting `Up`.

### 2. Decide on GitHub filtering

GitHub results are unfiltered, so an off-topic repository can appear in the feed (open question in the build checklist).

1. Without filtering: after the fresh ingestion (step 3), look through page 1 of the feed and pick the demo article from rows that are clearly on-topic.
2. With filtering: that's a code change with its own issue, PR and redeploy. It has to land before step 3, and it changes the working app, so it needs time to verify.

### 3. Refresh the articles on the live server

This writes new articles to the live database. Existing articles, bookmarks, keywords and votes stay as they are; reruns create no duplicates. Star counts and points of existing articles aren't refreshed.

1. Count the articles before:

   ```zsh
   echo "SELECT count(*) FROM articles_article;" | ssh -i ~/.ssh/devfeed_ec2 ubuntu@44.248.236.123 'cd ~/devfeed && docker compose exec -T db psql -U devfeed -d devfeed -tA'
   ```

2. Load the newest Hacker News stories (20 by default):

   ```zsh
   ssh -i ~/.ssh/devfeed_ec2 ubuntu@44.248.236.123 'cd ~/devfeed && docker compose exec -T backend python manage.py ingest_hacker_news'
   ```

3. Load the newest GitHub repositories (10 by default):

   ```zsh
   ssh -i ~/.ssh/devfeed_ec2 ubuntu@44.248.236.123 'cd ~/devfeed && docker compose exec -T backend python manage.py ingest_github'
   ```

4. Count the articles again with the command from item 1. The new count is the old count plus the new stories (stories already in the database are skipped).
5. Check the feed through the CLI; the footer count should match item 4:

   ```zsh
   devfeed --api-url 44.248.236.123 feed | head -6; devfeed --api-url 44.248.236.123 feed | tail -1
   ```

### 4. Choose the demo article

1. Pick an article id from page 1 of the live feed that is on-topic and not already saved by `live_test_user`:

   ```zsh
   devfeed --api-url 44.248.236.123 saved
   ```

2. Confirm `django` isn't already followed (it must not appear):

   ```zsh
   devfeed --api-url 44.248.236.123 keywords
   ```

3. Write the chosen id down for the talk.

### 5. Rehearse the full talk

1. Run through the outline with a timer; aim for 10 minutes or less.
2. Run the live demo exactly as written in the outline, using the chosen article id.
3. Clean up after each rehearsal so the live data is ready for the real demo. The demo's Delete step already removes the bookmark; this removes the keyword and the vote (replace `<id>` with the chosen article id):

   ```zsh
   devfeed --api-url 44.248.236.123 keywords unfollow django --yes; devfeed --api-url 44.248.236.123 unvote <id> --yes; devfeed --api-url 44.248.236.123 saved
   ```

   The last command confirms the demo bookmark is gone. If a rehearsal stopped before the Delete step, remove it with `devfeed --api-url 44.248.236.123 unsave <bookmark-id> --yes`, using the bookmark id that `saved` shows.

### 6. Record a backup demo

A recording covers a network or server failure during the presentation.

1. Do the morning-of setup below first, so the recording looks like the real demo.
2. Press **Cmd+Shift+5**, choose **Record Entire Screen** (or **Record Selected Portion**), and under **Options** pick a microphone to narrate, or **None**.
3. Click **Record** and run the live demo from the outline.
4. Stop with the stop button in the menu bar. The file is saved to the Desktop by default.
5. Play the recording back once to check it, then clean up the demo data as in step 5.3.

## On the day (Saturday, November 14)

### 7. Browser setup

1. In Brave, open `44.248.236.123` and confirm the app bar shows `live_test_user`. If it shows **Log in**, log in as `live_test_user` (password in the handoff notes).
2. Close DevTools.
3. Zoom the page so the room can read it (**Cmd+Plus**).
4. Close unrelated tabs.
5. For the optional GitHub section, open these four tabs after the DevFeed tab, in this order:
   1. `github.com/BigZeeke/devfeed` (repo layout)
   2. `github.com/BigZeeke/devfeed/pull/72` (the CLI pull request)
   3. `github.com/BigZeeke/devfeed/commits/main` (commit history)
   4. `github.com/BigZeeke/devfeed/issues?q=is%3Aissue+is%3Aclosed` (closed issues)
6. Zoom each GitHub tab too (**Cmd+Plus**), then switch back to the DevFeed tab.

### 8. Terminal setup

1. Open a new terminal tab, go to the repo, and activate the venv:

   ```zsh
   cd ~/Documents/Code_Platoon/devfeed && source venv/bin/activate
   ```

2. Point this tab at the live site and confirm the CLI session:

   ```zsh
   export DEVFEED_API_URL=44.248.236.123; devfeed whoami
   ```

   Expected: `Logged in as live_test_user on http://44.248.236.123`. If it says **Not logged in**, run `devfeed login` as `live_test_user`.

3. Clear the screen (`clear`) and increase the font size (**Cmd+Plus**) so the tables stay readable.
4. Check the feed loads: `devfeed feed | head -4`.

### 9. Final checks

1. Turn on Do Not Disturb so notifications don't appear on screen.
2. Keep the backup recording open in a paused player, in case the network fails.
3. Keep the chosen article id visible on paper or a second screen.

## During the demo

1. Don't run `devfeed logout`: the CLI and the browser share `live_test_user`'s token, so it would log the browser out too.
2. The browser shows CLI changes on the next page load or click, which is why `devfeed web saved` opens a fresh tab. The CLI shows browser changes on the next command.
3. If a command prints `Can't reach the DevFeed API`, check the network, then switch to the backup recording.

## After the presentation

1. Clean up the demo data as in step 5.3, or leave it.
2. Terminating the EC2 instance is a separate, irreversible decision (it deletes the live site and its data); it stays on the plan for later.
