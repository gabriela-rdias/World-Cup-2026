# 🏆 FIFA World Cup 2026 Prediction Game

A production-ready Streamlit web application for running a private World Cup prediction game between friends. No real money involved — just bragging rights and serious football knowledge.

---

## 📁 Project Structure

```
worldcup2026/
│
├── app.py                  # Main entry point — run this with Streamlit
├── database.py             # SQLAlchemy engine, session factory, DB init
├── models.py               # ORM models (User, Room, Match, Prediction, …)
├── scoring.py              # Scoring engine + leaderboard calculation
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
│
├── api/
│   └── football_api.py     # Football-Data.org API wrapper + caching
│
├── pages/
│   ├── auth_page.py        # Login / registration
│   ├── dashboard.py        # Main dashboard
│   ├── matches_page.py     # All matches + inline predictions
│   ├── predictions_page.py # Group standings + winner prediction hub
│   ├── leaderboard_page.py # Room leaderboard with podium
│   ├── teams_page.py       # Team browser + recent form
│   ├── rooms_page.py       # Create / join / manage rooms
│   └── admin_page.py       # Owner admin: sync, score, demo data
│
└── utils/
    ├── auth.py             # Password hashing + login/register logic
    ├── predictions.py      # Prediction CRUD operations
    ├── rooms.py            # Room creation, joining, deadline logic
    ├── standings.py        # Group table calculation from match results
    └── ui.py               # CSS injection, shared UI components
```

---

## ⚙️ Setup Instructions

### 1. Prerequisites

- Python 3.10 or higher
- pip

### 2. Clone / download the project

```bash
cd worldcup2026
```

### 3. Create and activate a virtual environment

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and add your API key:

```
FOOTBALL_API_KEY=your_key_here
```

> **Get a free API key** at [football-data.org](https://www.football-data.org/).
> The free tier gives you 10 requests/minute, which is enough for this app thanks to caching.
>
> **No API key?** The app still works fully with demo data.
> Use the **Admin → Demo Data** panel to load synthetic fixtures.

### 6. Run the app

```bash
streamlit run app.py
```

Open your browser at **http://localhost:8501**

---

## 🎮 How to Use

### First time setup
1. **Register** an account on the login screen.
2. Go to **Rooms** → Create a room and note your invite code.
3. Share the invite code with friends so they can join.

### Making predictions
| Prediction type | Where | Points |
|---|---|---|
| Match result (W/D/L) | Matches page or Dashboard | 1–10 pts by round |
| Group standings (1st–4th) | Predictions page | 1–3 pts per group |
| Tournament winner | Dashboard or Predictions | 15 pts |

### Scoring (room owner)
1. Go to **Admin → Scoring**.
2. After matches finish, click **"Score All Finished Matches"**.
3. After the group stage, score each group's standings.
4. At the end of the tournament, award tournament winner points.

### Deadline types (set per room)
| Setting | Behaviour |
|---|---|
| 1 hour before kickoff | Default — predictions lock 60 min before the game |
| Day before match | Predictions close at midnight the day before |
| Fixed window | Owner sets a custom hour window after matchups are announced |

---

## 📡 API Integration

The app uses **Football-Data.org v4** (free tier).

| Endpoint used | Purpose |
|---|---|
| `/competitions/WC/teams` | Team names, crests |
| `/competitions/WC/matches` | All fixtures + live scores |
| `/competitions/WC/standings` | Live group tables |
| `/teams/{id}/matches` | Recent form (Teams page) |

All API responses are cached in SQLite (`api_cache` table) with configurable TTLs:
- Static data (teams): 24 hours
- Match results: 10 minutes
- Live scores: 1 hour default

---

## 🧮 Scoring Rules

| Round | Points for correct result |
|---|---|
| Group Stage | 1 pt |
| Round of 32 (16-avos) | 2 pts |
| Round of 16 | 4 pts |
| Quarter-Finals | 6 pts |
| Semi-Finals | 8 pts |
| Final | 10 pts |

**Group Standings:**
- 2+ correct positions in the group → 1 pt
- All 4 positions correct → 3 pts

**Tournament Winner:** 15 pts (set before the tournament starts)

---

## 🔒 Security Notes

- Passwords are hashed using **bcrypt** (never stored in plain text).
- Sessions are managed via Streamlit's `st.session_state` (no cookies).
- SQLite WAL mode is enabled for better concurrency.
- This app is designed for **local/private use** between friends.
- For public deployment, add HTTPS and consider moving to PostgreSQL.

---

## 🚀 Production Deployment Tips

To deploy on a server (e.g. an EC2 instance or Render.com):

1. Set `FOOTBALL_API_KEY` as a server environment variable (not in `.env`).
2. Use a process manager like `tmux` or `systemd` to keep the app running:
   ```bash
   streamlit run app.py --server.port 8501 --server.headless true
   ```
3. Put **Nginx** in front as a reverse proxy with SSL.
4. For multi-user deployments, migrate from SQLite to **PostgreSQL** by changing `DATABASE_URL` in `database.py`.

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `streamlit` | Web framework |
| `sqlalchemy` | ORM / database |
| `bcrypt` | Password hashing |
| `requests` | HTTP API calls |
| `pandas` | Leaderboard charts |
| `python-dotenv` | .env loading |

---

## 📄 License

MIT — use freely for personal and educational purposes.

---

*Built for the 2026 FIFA World Cup · USA · Canada · Mexico*
