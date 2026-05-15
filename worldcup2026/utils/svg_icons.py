"""
utils/svg_icons.py — SVG icon library replacing all emoji usage.
Returns inline SVG strings for use in st.markdown(unsafe_allow_html=True).
"""

def icon(name: str, size: int = 18, color: str = "currentColor", style: str = "") -> str:
    s = str(size)
    base = f'width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{style}"'
    icons = {
        # Nav / UI
        "settings":    f'<svg {base}><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93l-1.41 1.41M5.34 17.66l-1.41 1.41M20 12h-2M6 12H4M19.07 19.07l-1.41-1.41M5.34 6.34L3.93 4.93M12 2v2M12 20v2"/></svg>',
        "warning":     f'<svg {base}><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
        "crown":       f'<svg {base}><path d="M2 20h20M4 20l2-8 6 4 6-4 2 8"/><circle cx="12" cy="8" r="2"/></svg>',
        "satellite":   f'<svg {base}><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m3.5 11.5 5 5"/><path d="M20 4l-6.5 6.5"/><path d="m14 4 6 6"/><path d="m4 14 6-6"/></svg>',
        "calculator":  f'<svg {base}><rect x="4" y="2" width="16" height="20" rx="2"/><line x1="8" y1="6" x2="16" y2="6"/><line x1="8" y1="10" x2="16" y2="10"/><line x1="8" y1="14" x2="12" y2="14"/><line x1="8" y1="18" x2="10" y2="18"/></svg>',
        "gamepad":     f'<svg {base}><rect x="2" y="6" width="20" height="12" rx="4"/><line x1="6" y1="12" x2="10" y2="12"/><line x1="8" y1="10" x2="8" y2="14"/><circle cx="15" cy="11" r="1" fill="{color}"/><circle cx="17" cy="13" r="1" fill="{color}"/></svg>',
        "danger":      f'<svg {base}><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
        "sync":        f'<svg {base}><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>',
        "trash":       f'<svg {base}><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>',
        "check":       f'<svg {base}><polyline points="20 6 9 17 4 12"/></svg>',
        "x":           f'<svg {base}><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
        "info":        f'<svg {base}><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
        "refresh":     f'<svg {base}><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-4"/></svg>',
        "dice":        f'<svg {base}><rect x="2" y="2" width="20" height="20" rx="3"/><circle cx="8" cy="8" r="1.2" fill="{color}"/><circle cx="16" cy="8" r="1.2" fill="{color}"/><circle cx="8" cy="16" r="1.2" fill="{color}"/><circle cx="16" cy="16" r="1.2" fill="{color}"/><circle cx="12" cy="12" r="1.2" fill="{color}"/></svg>',
        "bulb":        f'<svg {base}><line x1="9" y1="18" x2="15" y2="18"/><line x1="10" y1="21" x2="14" y2="21"/><path d="M12 2a7 7 0 0 1 7 7c0 2.9-1.76 5.39-4.32 6.56L14 18H10l-.68-2.44A7 7 0 0 1 12 2z"/></svg>',
        # Status dots
        "dot-win":     f'<svg width="{s}" height="{s}" viewBox="0 0 10 10" style="vertical-align:middle;{style}"><circle cx="5" cy="5" r="4" fill="#22c55e"/></svg>',
        "dot-draw":    f'<svg width="{s}" height="{s}" viewBox="0 0 10 10" style="vertical-align:middle;{style}"><circle cx="5" cy="5" r="4" fill="#eab308"/></svg>',
        "dot-loss":    f'<svg width="{s}" height="{s}" viewBox="0 0 10 10" style="vertical-align:middle;{style}"><circle cx="5" cy="5" r="4" fill="#ef4444"/></svg>',
        "dot-none":    f'<svg width="{s}" height="{s}" viewBox="0 0 10 10" style="vertical-align:middle;{style}"><circle cx="5" cy="5" r="4" fill="#555"/></svg>',
        # World 2022 mode
        "globe":       f'<svg {base}><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>',
        "live":        f'<svg {base}><circle cx="12" cy="12" r="3" fill="{color}"/><path d="M6.3 6.3a8 8 0 0 0 0 11.4"/><path d="M17.7 6.3a8 8 0 0 1 0 11.4"/><path d="M3.5 3.5a14 14 0 0 0 0 19.8"/><path d="M20.5 3.5a14 14 0 0 1 0 19.8"/></svg>',
    }
    return icons.get(name, f'<svg {base}><circle cx="12" cy="12" r="8"/></svg>')


# Football-only avatar SVG icons — returns (label, svg_string) pairs
FOOTBALL_AVATARS = [
    ("Ball",      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 2c0 0-2 4-2 10s2 10 2 10"/><path d="M2 12h20"/><path d="M4.5 6.5l3.5 2.5-1 4 4 1.5 4-1.5-1-4 3.5-2.5"/></svg>'),
    ("Trophy",    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-1a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v1a2 2 0 0 1-2 2h-2"/><rect x="6" y="18" width="12" height="4"/></svg>'),
    ("Boot",      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 18h13l2-6-4-2-2-5H8l1 5-4 3v5z"/><line x1="3" y1="18" x2="20" y2="18"/><line x1="9" y1="18" x2="9" y2="20"/><line x1="15" y1="18" x2="15" y2="20"/></svg>'),
    ("Goal",      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="4" width="20" height="14" rx="1"/><line x1="12" y1="4" x2="12" y2="18"/><line x1="2" y1="11" x2="22" y2="11"/><path d="M2 18 Q12 22 22 18"/></svg>'),
    ("Jersey",    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 5l3-2 2 3h8l2-3 3 2-2 4h-2v10H8V9H6z"/></svg>'),
    ("Whistle",   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M6 12a6 6 0 1 0 12 0"/><path d="M6 12H2l4-8h10l2 4"/><line x1="14" y1="8" x2="14" y2="12"/></svg>'),
    ("Flag",      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><line x1="4" y1="3" x2="4" y2="21"/><path d="M4 4l14 4-14 4"/></svg>'),
    ("Gloves",    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M18 11V7a3 3 0 0 0-3-3 3 3 0 0 0-3 3v4"/><path d="M12 11V5a3 3 0 0 0-3-3 3 3 0 0 0-3 3v6"/><path d="M6 11a4 4 0 0 0 4 4h4a4 4 0 0 0 4-4v-1H6z"/><path d="M6 15v2a4 4 0 0 0 4 4h4a4 4 0 0 0 4-4v-2"/></svg>'),
]

def avatar_svg(label: str, size: int = 32, color: str = "#C8102E") -> str:
    for lbl, svg in FOOTBALL_AVATARS:
        if lbl == label:
            return svg.replace('stroke="currentColor"', f'stroke="{color}"').replace(
                '<svg ', f'<svg width="{size}" height="{size}" ')
    return FOOTBALL_AVATARS[0][1]

def result_dots(results: list[str]) -> str:
    """Convert list of 'win'/'draw'/'loss'/None to SVG dots."""
    map_ = {"win": "dot-win", "draw": "dot-draw", "loss": "dot-loss", None: "dot-none", "none": "dot-none"}
    return " ".join(icon(map_.get(r, "dot-none"), 10) for r in results)
