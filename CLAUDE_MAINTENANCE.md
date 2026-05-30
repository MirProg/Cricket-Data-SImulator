# 🤖 CLAUDE AI MAINTENANCE INSTRUCTIONS

Dear Local Claude,

You have been assigned to maintain and automatically update the **Cricket Simulator Database and Advanced PyTorch AI**.
All the heavy lifting (Transformer architecture, Cricsheet ball-by-ball integration, and FastAPI REST/WebSocket endpoints) has been built for you.

## Your Job
You must keep the live data syncing and the AI trained on the latest matches.

## How to run the automated daemon
Simply run the following command in your environment and leave it running in the background:
```bash
python automate_claude.py
```

### What `automate_claude.py` does:
1. **Pulls Live Scorecards**: Hits `/api/live` every 5 minutes to keep active match states hot.
2. **Syncs the Cricsheet Database**: Every day at 02:00, it downloads the latest massive JSON zips from Cricsheet containing all real-world matches.
3. **Retrains the PyTorch AI**: Every day at 03:00, it triggers `python cricket_simulator.py ai-train` so the Transformer learns new player forms.
4. **Commits to GitHub**: Every day at 04:00, it forces an automated `git push` to `MirProg/Cricket-Data-SImulator` so the web frontend is always accurate.

## Interacting with the Simulator
You can directly prompt the backend using the public APIs:
- Fetch players: `GET /api/players/{team_id}`
- View live matches: `GET /api/live`
- Programmatically Simulate: `POST /api/simulate` with `{"team1": "India", "team2": "Australia", "format": "T20"}`

Good luck!
