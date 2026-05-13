"""
utils/wc2022_data.py
Real World Cup 2022 (Qatar) data for the "2022 Mode" demo.
All matches, groups, results and knockout bracket — fully scoreable.
"""
from datetime import datetime
from models import MatchStage

# ── Teams (id 100+ to avoid clashing with 2026 teams) ─────────────────
WC2022_TEAMS = [
    {"id":101,"name":"Qatar",         "shortName":"Qatar",       "tla":"QAT","group":"A"},
    {"id":102,"name":"Ecuador",       "shortName":"Ecuador",     "tla":"ECU","group":"A"},
    {"id":103,"name":"Senegal",       "shortName":"Senegal",     "tla":"SEN","group":"A"},
    {"id":104,"name":"Netherlands",   "shortName":"Netherlands", "tla":"NED","group":"A"},
    {"id":105,"name":"England",       "shortName":"England",     "tla":"ENG","group":"B"},
    {"id":106,"name":"Iran",          "shortName":"Iran",        "tla":"IRN","group":"B"},
    {"id":107,"name":"USA",           "shortName":"USA",         "tla":"USA","group":"B"},
    {"id":108,"name":"Wales",         "shortName":"Wales",       "tla":"WAL","group":"B"},
    {"id":109,"name":"Argentina",     "shortName":"Argentina",   "tla":"ARG","group":"C"},
    {"id":110,"name":"Saudi Arabia",  "shortName":"S. Arabia",   "tla":"KSA","group":"C"},
    {"id":111,"name":"Mexico",        "shortName":"Mexico",      "tla":"MEX","group":"C"},
    {"id":112,"name":"Poland",        "shortName":"Poland",      "tla":"POL","group":"C"},
    {"id":113,"name":"France",        "shortName":"France",      "tla":"FRA","group":"D"},
    {"id":114,"name":"Australia",     "shortName":"Australia",   "tla":"AUS","group":"D"},
    {"id":115,"name":"Denmark",       "shortName":"Denmark",     "tla":"DEN","group":"D"},
    {"id":116,"name":"Tunisia",       "shortName":"Tunisia",     "tla":"TUN","group":"D"},
    {"id":117,"name":"Spain",         "shortName":"Spain",       "tla":"ESP","group":"E"},
    {"id":118,"name":"Costa Rica",    "shortName":"Costa Rica",  "tla":"CRC","group":"E"},
    {"id":119,"name":"Germany",       "shortName":"Germany",     "tla":"GER","group":"E"},
    {"id":120,"name":"Japan",         "shortName":"Japan",       "tla":"JPN","group":"E"},
    {"id":121,"name":"Belgium",       "shortName":"Belgium",     "tla":"BEL","group":"F"},
    {"id":122,"name":"Canada",        "shortName":"Canada",      "tla":"CAN","group":"F"},
    {"id":123,"name":"Morocco",       "shortName":"Morocco",     "tla":"MAR","group":"F"},
    {"id":124,"name":"Croatia",       "shortName":"Croatia",     "tla":"CRO","group":"F"},
    {"id":125,"name":"Brazil",        "shortName":"Brazil",      "tla":"BRA","group":"G"},
    {"id":126,"name":"Serbia",        "shortName":"Serbia",      "tla":"SRB","group":"G"},
    {"id":127,"name":"Switzerland",   "shortName":"Switzerland", "tla":"SUI","group":"G"},
    {"id":128,"name":"Cameroon",      "shortName":"Cameroon",    "tla":"CMR","group":"G"},
    {"id":129,"name":"Portugal",      "shortName":"Portugal",    "tla":"POR","group":"H"},
    {"id":130,"name":"Ghana",         "shortName":"Ghana",       "tla":"GHA","group":"H"},
    {"id":131,"name":"Uruguay",       "shortName":"Uruguay",     "tla":"URU","group":"H"},
    {"id":132,"name":"South Korea",   "shortName":"S. Korea",    "tla":"KOR","group":"H"},
]

TEAM_FLAGS = {
    101:"🇶🇦",102:"🇪🇨",103:"🇸🇳",104:"🇳🇱",105:"🏴󠁧󠁢󠁥󠁮󠁧󠁿",106:"🇮🇷",107:"🇺🇸",108:"🏴󠁧󠁢󠁷󠁬󠁳󠁿",
    109:"🇦🇷",110:"🇸🇦",111:"🇲🇽",112:"🇵🇱",113:"🇫🇷",114:"🇦🇺",115:"🇩🇰",116:"🇹🇳",
    117:"🇪🇸",118:"🇨🇷",119:"🇩🇪",120:"🇯🇵",121:"🇧🇪",122:"🇨🇦",123:"🇲🇦",124:"🇭🇷",
    125:"🇧🇷",126:"🇷🇸",127:"🇨🇭",128:"🇨🇲",129:"🇵🇹",130:"🇬🇭",131:"🇺🇾",132:"🇰🇷",
}

# ── Group stage results ────────────────────────────────────────────────
# (id, home_id, away_id, home_score, away_score, matchday, group)
GROUP_MATCHES = [
    # Group A
    (2001,101,102, 0,2,1,"A"),(2002,103,104, 0,2,1,"A"),
    (2003,101,103, 1,3,2,"A"),(2004,104,102, 1,1,2,"A"),
    (2005,104,101, 2,0,3,"A"),(2006,102,103, 1,2,3,"A"),
    # Group B
    (2007,105,106, 6,2,1,"B"),(2008,107,108, 1,1,1,"B"),
    (2009,108,106, 0,2,2,"B"),(2010,105,107, 0,0,2,"B"),
    (2011,108,105, 0,3,3,"B"),(2012,106,107, 0,1,3,"B"),
    # Group C
    (2013,109,110, 1,2,1,"C"),(2014,111,112, 0,0,1,"C"),
    (2015,109,111, 2,0,2,"C"),(2016,112,110, 2,0,2,"C"),
    (2017,112,109, 0,2,3,"C"),(2018,110,111, 1,2,3,"C"),
    # Group D
    (2019,113,114, 4,1,1,"D"),(2020,115,116, 0,0,1,"D"),
    (2021,113,115, 2,1,2,"D"),(2022,116,114, 0,1,2,"D"),
    (2023,116,113, 1,0,3,"D"),(2024,114,115, 1,0,3,"D"),
    # Group E
    (2025,117,118, 7,0,1,"E"),(2026,119,120, 1,2,1,"E"),
    (2027,117,119, 1,1,2,"E"),(2028,120,118, 4,0,2,"E"),
    (2029,120,117, 2,1,3,"E"),(2030,118,119, 2,4,3,"E"),
    # Group F
    (2031,121,122, 1,0,1,"F"),(2032,123,124, 0,0,1,"F"),
    (2033,121,123, 0,2,2,"F"),(2034,124,122, 4,1,2,"F"),
    (2035,124,121, 0,0,3,"F"),(2036,122,123, 1,2,3,"F"),
    # Group G
    (2037,125,126, 2,0,1,"G"),(2038,127,128, 1,0,1,"G"),
    (2039,125,127, 1,0,2,"G"),(2040,128,126, 3,3,2,"G"),
    (2041,128,125, 1,0,3,"G"),(2042,126,127, 2,3,3,"G"),
    # Group H
    (2043,129,130, 3,2,1,"H"),(2044,131,132, 0,0,1,"H"),
    (2045,129,131, 2,0,2,"H"),(2046,132,130, 2,3,2,"H"),
    (2047,132,129, 2,1,3,"H"),(2048,130,131, 0,2,3,"H"),
]

# ── Knockout matches ────────────────────────────────────────────────────
# Round of 16
KNOCKOUT_MATCHES = [
    (2101,104,107, 3,1,MatchStage.ROUND_OF_16,None),  # Netherlands vs USA
    (2102,109,114, 2,1,MatchStage.ROUND_OF_16,None),  # Argentina vs Australia
    (2103,113,112, 3,1,MatchStage.ROUND_OF_16,None),  # France vs Poland
    (2104,105,103, 3,0,MatchStage.ROUND_OF_16,None),  # England vs Senegal
    (2105,120,124, 1,1,MatchStage.ROUND_OF_16,None),  # Japan vs Croatia (Croatia on pens)
    (2106,123,117, 0,0,MatchStage.ROUND_OF_16,None),  # Morocco vs Spain (Morocco on pens)
    (2107,125,132, 4,1,MatchStage.ROUND_OF_16,None),  # Brazil vs S. Korea
    (2108,129,127, 6,1,MatchStage.ROUND_OF_16,None),  # Portugal vs Switzerland
    # Quarter-finals
    (2201,104,109, 2,2,MatchStage.QUARTER,None),   # Netherlands vs Argentina (Argentina pens)
    (2202,113,105, 2,1,MatchStage.QUARTER,None),   # France vs England
    (2203,124,125, 1,1,MatchStage.QUARTER,None),   # Croatia vs Brazil (Croatia pens)
    (2204,123,129, 1,0,MatchStage.QUARTER,None),   # Morocco vs Portugal
    # Semi-finals
    (2301,109,124, 3,0,MatchStage.SEMI,None),   # Argentina vs Croatia
    (2302,113,123, 2,0,MatchStage.SEMI,None),   # France vs Morocco
    # Third place play-off
    (2401,124,123, 2,1,MatchStage.THIRD_PLACE,None),  # Croatia vs Morocco (3rd place)
    # Final
    (2501,109,113, 3,3,MatchStage.FINAL,None),  # Argentina vs France (Argentina on pens)
]

# Final group standings (position order per group)
GROUP_STANDINGS_2022 = {
    "A": [104,103,102,101],
    "B": [105,107,106,108],
    "C": [109,112,111,110],
    "D": [113,114,115,116],
    "E": [120,117,119,118],
    "F": [123,124,121,122],
    "G": [125,127,128,126],
    "H": [129,132,131,130],
}

WINNER_2022 = 109  # Argentina

def get_team_by_id(team_id: int) -> dict:
    for t in WC2022_TEAMS:
        if t["id"] == team_id:
            return t
    return {"id": team_id, "name": "Unknown", "shortName": "UNK", "tla": "UNK"}

def get_teams_by_group() -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for t in WC2022_TEAMS:
        groups.setdefault(t["group"], []).append(t)
    return groups
