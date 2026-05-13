"""
pages/news_page.py — World Cup news via NewsAPI (free tier) with web search fallback.
Requires NEWSAPI_KEY in .env for live data. Falls back to curated static links otherwise.
"""
import os, time
import streamlit as st
import requests
from datetime import datetime, timedelta
from utils.ui import inject_css, page_header, require_login, svg_icon

NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", "")

CATEGORIES = {
    "All World Cup":    "FIFA World Cup 2026",
    "Argentina":        "Argentina football 2026",
    "Brazil":           "Brazil football 2026",
    "France":           "France football 2026",
    "England":          "England football 2026",
    "Spain":            "Spain football 2026",
    "Portugal":         "Portugal football 2026",
    "Germany":          "Germany football 2026",
    "Morocco":          "Morocco football 2026",
}

STATIC_ARTICLES = [
    {
        "title": "FIFA World Cup 2026: Everything You Need to Know",
        "description": "The 2026 World Cup will be hosted across USA, Canada and Mexico — the first edition with 48 teams and 104 matches.",
        "url": "https://www.fifa.com/en/tournaments/mens/worldcup/canada-mexico-usa2026",
        "source": "FIFA Official",
        "publishedAt": "2026-01-01T00:00:00Z",
        "urlToImage": None,
    },
    {
        "title": "World Cup 2026 Groups & Format Explained",
        "description": "For the first time, 48 nations compete in 12 groups of 4, with the top 2 plus 8 best third-placed teams advancing.",
        "url": "https://www.fifa.com/en/tournaments/mens/worldcup/canada-mexico-usa2026/articles",
        "source": "FIFA Official",
        "publishedAt": "2026-02-01T00:00:00Z",
        "urlToImage": None,
    },
    {
        "title": "Host Cities for FIFA World Cup 2026",
        "description": "16 cities across USA, Canada and Mexico will host matches — including New York, Los Angeles, Dallas and Mexico City.",
        "url": "https://www.fifa.com/en/tournaments/mens/worldcup/canada-mexico-usa2026/destination",
        "source": "FIFA Official",
        "publishedAt": "2026-02-15T00:00:00Z",
        "urlToImage": None,
    },
    {
        "title": "Qualification: Which Teams Have Made It to USA/Canada/Mexico?",
        "description": "Teams from Europe, South America, Africa, Asia and CONCACAF battle for the 48 spots at the expanded World Cup.",
        "url": "https://www.bbc.com/sport/football/world-cup",
        "source": "BBC Sport",
        "publishedAt": "2026-03-01T00:00:00Z",
        "urlToImage": None,
    },
    {
        "title": "Top Favourites & Dark Horses for World Cup 2026",
        "description": "Argentina defend their title while Brazil, France, England and Spain are all expected to challenge for glory.",
        "url": "https://www.goal.com/en/world-cup",
        "source": "Goal.com",
        "publishedAt": "2026-03-10T00:00:00Z",
        "urlToImage": None,
    },
    {
        "title": "World Cup 2026 Schedule: Full Fixture List",
        "description": "Group stage begins June 11. Round of 32 starts June 29. The final is July 19 at MetLife Stadium, New Jersey.",
        "url": "https://www.fifa.com/en/tournaments/mens/worldcup/canada-mexico-usa2026/match-schedule",
        "source": "FIFA Official",
        "publishedAt": "2026-03-15T00:00:00Z",
        "urlToImage": None,
    },
]


@st.cache_data(ttl=600)  # cache 10 minutes
def _fetch_news(query: str) -> list[dict]:
    if not NEWSAPI_KEY:
        return []
    try:
        from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": 12,
            "from": from_date,
            "apiKey": NEWSAPI_KEY,
        }
        r = requests.get(url, params=params, timeout=8)
        data = r.json()
        return data.get("articles", [])
    except Exception:
        return []


def _article_card(article: dict, idx: int):
    title       = article.get("title", "No title") or "No title"
    description = article.get("description", "") or ""
    url         = article.get("url", "#") or "#"
    source      = (article.get("source") or {})
    source_name = source.get("name", "") if isinstance(source, dict) else str(source)
    published   = article.get("publishedAt", "") or ""
    image       = article.get("urlToImage", None)

    # Format date
    try:
        dt = datetime.fromisoformat(published.replace("Z", ""))
        date_str = dt.strftime("%d %b %Y")
    except Exception:
        date_str = published[:10] if published else ""

    # Truncate description
    if len(description) > 160:
        description = description[:157] + "…"

    img_html = ""
    if image:
        img_html = f'<img src="{image}" style="width:100%;height:140px;object-fit:cover;border-radius:8px 8px 0 0;" onerror="this.style.display=\'none\'" />'

    st.markdown(
        f"""
        <a href="{url}" target="_blank" style="text-decoration:none;">
        <div style="background:var(--surface2);border:1px solid var(--border);
            border-radius:var(--radius);overflow:hidden;margin-bottom:12px;
            transition:border-color 0.2s, transform 0.2s;
            box-shadow:var(--shadow-sm);"
            onmouseover="this.style.borderColor='#B71C1C';this.style.transform='translateY(-2px)'"
            onmouseout="this.style.borderColor='var(--border)';this.style.transform='translateY(0)'">
            {img_html}
            <div style="padding:14px 16px;">
                <div style="font-size:0.7rem;color:var(--text-muted);margin-bottom:6px;
                    display:flex;justify-content:space-between;">
                    <span style="color:var(--primary);font-weight:600;">{source_name}</span>
                    <span>{date_str}</span>
                </div>
                <div style="font-size:0.9rem;font-weight:600;color:var(--text);
                    line-height:1.4;margin-bottom:8px;">{title}</div>
                <div style="font-size:0.78rem;color:var(--text-muted);line-height:1.5;">
                    {description}</div>
                <div style="margin-top:10px;font-size:0.72rem;color:var(--primary);
                    font-weight:600;display:flex;align-items:center;gap:4px;">
                    {svg_icon("link",12,"#B71C1C")} Read more
                </div>
            </div>
        </div>
        </a>
        """,
        unsafe_allow_html=True,
    )


def render():
    inject_css()
    require_login()

    page_header("NEWS", "Latest World Cup & national team updates")

    # ── Setup instructions if no key ──────────────────────────────────
    if not NEWSAPI_KEY:
        st.info(
            f"{svg_icon('globe',14,'#1565C0')} &nbsp;"
            "**Live news** requires a free NewsAPI key. "
            "Get one at [newsapi.org](https://newsapi.org) (free tier: 100 requests/day), "
            "then add `NEWSAPI_KEY=your_key` to your `.env` file. "
            "Showing curated links in the meantime.",
            )

    # ── Category selector ─────────────────────────────────────────────
    col_cat, col_refresh = st.columns([4, 1])
    with col_cat:
        category = st.selectbox(
            "Topic",
            options=list(CATEGORIES.keys()),
            label_visibility="collapsed",
        )
    with col_refresh:
        if st.button("Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    query = CATEGORIES[category]

    # ── Fetch or fallback ─────────────────────────────────────────────
    with st.spinner("Loading latest news…"):
        articles = _fetch_news(query)

    if not articles:
        # Show static curated articles
        articles = STATIC_ARTICLES
        st.markdown(
            f'<p style="color:var(--text-muted);font-size:0.8rem;margin-bottom:16px;">'
            f'{svg_icon("clock",13,"#B8960C")} Showing curated World Cup links '
            f'(add NEWSAPI_KEY to .env for live articles)</p>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<p style="color:var(--text-muted);font-size:0.8rem;margin-bottom:16px;">'
            f'{svg_icon("check",13,"#2E7D32")} {len(articles)} articles · '
            f'Updated just now · Topic: <strong style="color:var(--text);">{category}</strong></p>',
            unsafe_allow_html=True,
        )

    # ── 3-column article grid ─────────────────────────────────────────
    cols = st.columns(3)
    for idx, article in enumerate(articles):
        with cols[idx % 3]:
            _article_card(article, idx)

    # ── Footer tip ────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        f'<div style="text-align:center;color:var(--text-dim);font-size:0.75rem;">'
        f'Articles open in a new tab · News powered by NewsAPI</div>',
        unsafe_allow_html=True,
    )
