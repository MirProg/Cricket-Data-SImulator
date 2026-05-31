# Cricket Database Master Initialization Plan (4-Hour Automation Task)

You have been invoked to act as a fully autonomous agent for the next 4 hours. Your goal is to completely finalize the Cricket Database Application. 

The previous AI (Antigravity) has already built the Next.js 15 App Router structure and FastAPI endpoints, including the massive Sidebar megamenu with categories like Series, Matches By Day, Teams, Archives, Leagues, and Records. However, the data feeding into these pages is currently mocked or incomplete. 

You must execute the following phases completely autonomously:

## Phase 1: Massive Data Scraping & Organization
1. **Download & Scrape**: Use Python scripts to download all remaining required data from Cricsheet, Cricinfo, or CricketArchive. This includes:
   - Match by Match ball data (T20, ODI, Test) for the 900,000+ matches.
   - Comprehensive Player Profiles (Career stats, averages, strike rates).
   - Global Records (Highest run scorers, most wickets, etc. across all formats).
   - Series and League schedules and point tables.
2. **Database Seeding**: Completely rebuild the SQLite database (`data/schema.sql` and `data/seed_mock_db.py` or new scripts) to ingest this real data cleanly. Drop all mocked data.

## Phase 2: UI/UX Data Linking
1. **Wire up Endpoints**: Go into `web/app.py` and modify the FastAPI endpoints (`/api/series`, `/api/archives/{year}`, `/api/team/{team_name}`, `/api/league/{league_id}`, `/api/records/{format}`) to query the real SQLite data you just ingested.
2. **Frontend UI Fixes**: Go into the Next.js pages (e.g. `frontend/src/app/match/[id]/page.js`) and ensure that the incoming real data perfectly maps to the UI. Ensure that there are absolutely NO overlapping tables, missing data bugs, or broken Tailwind layouts when massive arrays of data are rendered.
3. **Sidebar Validation**: Ensure every single link in the `Sidebar.js` megamenu accurately links to a working page populated with real data.

## Phase 3: Version Control (Git Updation)
- You MUST commit your progress to Git frequently.
- Every time you finish a significant milestone (e.g., "Finished data scraping", "Wired up Series UI"), run `git add .` and `git commit -m "feat: [describe feature]"`.
- Keep the git history clean and descriptive.

## Execution Rules:
- The user is watching you run in the foreground. You can ask for their guidance if absolutely necessary, but attempt to solve all problems autonomously.
- Do not stop until all data is fully linked to the UI and everything looks professional.
- Begin immediately!
