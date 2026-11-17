#!/usr/bin/env python3
"""Generates blackhole.svg: an animated black hole for a GitHub profile README.
Pure SVG + SMIL (no scripts), so it animates inside GitHub's <img> sandbox."""
import datetime, json, math, os, random, sys, urllib.request

LOGIN = os.environ.get("GITHUB_REPOSITORY_OWNER", "ashwanijha-branch")
QUERY = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
totalContributions weeks{contributionDays{date contributionCount}}}}}}"""

def fetch_stats():
    """Real numbers for the HUD. Returns None when no token is available."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        return None
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "profile-readme"})
    body = json.load(urllib.request.urlopen(req, timeout=30))
    if body.get("errors"):
        sys.exit(f"GitHub API error: {body['errors']}")
    cal = body["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    days = [d for d in days if d["date"] <= today]
    counts = [d["contributionCount"] for d in days]
    tail = counts[:-1] if counts and counts[-1] == 0 else counts   # today may still be empty
    streak = 0
    for c in reversed(tail):
        if c == 0:
            break
        streak += 1
    active = [d["date"] for d in days if d["contributionCount"]]
    return {"total": cal["totalContributions"], "streak": streak,
            "peak": max(counts, default=0), "last": active[-1] if active else "--"}

STATS = fetch_stats()
def stat(key, fmt="{}"):
    return fmt.format(STATS[key]) if STATS else "--"

random.seed(7)
W, H = 1200, 520
CX, CY = 600, 250
RS = 62            # shadow radius
TILT = 0.11        # disk flattening (near edge-on)
R_IN, R_OUT = 84, 370

def lerp(a, b, t): return a + (b - a) * t

STOPS = [(0.0, (255, 246, 222)), (0.18, (255, 208, 128)), (0.42, (255, 140, 60)),
         (0.72, (190, 62, 14)), (1.0, (84, 22, 10))]

def heat(t):
    for (t0, c0), (t1, c1) in zip(STOPS, STOPS[1:]):
        if t <= t1:
            k = (t - t0) / (t1 - t0)
            return "#%02x%02x%02x" % tuple(round(lerp(a, b, k)) for a, b in zip(c0, c1))
    return "#54160a"

def dashes(r, lo, hi):
    """Random dash pattern that closes exactly on the circumference."""
    c = 2 * math.pi * r
    n = random.randint(lo, hi)
    parts = [random.uniform(0.4, 1.6) for _ in range(2 * n)]
    s = c / sum(parts)
    return " ".join(f"{p * s:.1f}" for p in parts)

def ring(r, width, color, opacity, dur, lo=3, hi=7):
    start = random.uniform(0, 360)
    return (f'<circle r="{r:.1f}" fill="none" stroke="{color}" stroke-width="{width:.1f}" '
            f'stroke-opacity="{opacity:.2f}" stroke-dasharray="{dashes(r, lo, hi)}">'
            f'<animateTransform attributeName="transform" type="rotate" from="{start:.0f}" '
            f'to="{start - 360:.0f}" dur="{dur:.1f}s" repeatCount="indefinite"/></circle>')

out = []
A = out.append
A(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
  f'aria-label="Animated black hole with a glowing accretion disk">')
A('''<defs>
<radialGradient id="sky" cx="50%" cy="48%" r="75%">
 <stop offset="0" stop-color="#0d0a1c"/><stop offset=".55" stop-color="#06060f"/><stop offset="1" stop-color="#020206"/>
</radialGradient>
<radialGradient id="nebA"><stop offset="0" stop-color="#5b2a86" stop-opacity=".30"/><stop offset="1" stop-color="#5b2a86" stop-opacity="0"/></radialGradient>
<radialGradient id="nebB"><stop offset="0" stop-color="#0e6b7a" stop-opacity=".22"/><stop offset="1" stop-color="#0e6b7a" stop-opacity="0"/></radialGradient>
<radialGradient id="aura">
 <stop offset="0" stop-color="#ffb060" stop-opacity=".55"/><stop offset=".35" stop-color="#ff7a2a" stop-opacity=".20"/>
 <stop offset=".7" stop-color="#b3360a" stop-opacity=".06"/><stop offset="1" stop-color="#b3360a" stop-opacity="0"/>
</radialGradient>
<radialGradient id="diskGlow">
 <stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".215" stop-color="#fff" stop-opacity="0"/>
 <stop offset=".235" stop-color="#fff3d0" stop-opacity=".95"/><stop offset=".40" stop-color="#ffab4a" stop-opacity=".85"/>
 <stop offset=".70" stop-color="#c2410c" stop-opacity=".45"/><stop offset="1" stop-color="#5b1a0a" stop-opacity="0"/>
</radialGradient>
<radialGradient id="haloGlow">
 <stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".50" stop-color="#fff" stop-opacity="0"/>
 <stop offset=".53" stop-color="#fff6dc" stop-opacity=".95"/><stop offset=".68" stop-color="#ff9a3c" stop-opacity=".50"/>
 <stop offset="1" stop-color="#b3360a" stop-opacity="0"/>
</radialGradient>
<linearGradient id="doppler" gradientUnits="userSpaceOnUse" x1="-380" y1="0" x2="380" y2="0">
 <stop offset="0" stop-color="#fff"/><stop offset=".45" stop-color="#ddd"/><stop offset="1" stop-color="#7a7a7a"/>
</linearGradient>
<linearGradient id="haloFade" gradientUnits="userSpaceOnUse" x1="0" y1="-130" x2="0" y2="130">
 <stop offset="0" stop-color="#fff"/><stop offset=".5" stop-color="#eee"/><stop offset="1" stop-color="#666"/>
</linearGradient>
<linearGradient id="jet" x1="0" y1="1" x2="0" y2="0">
 <stop offset="0" stop-color="#9fd8ff" stop-opacity=".55"/><stop offset=".4" stop-color="#5aa9ff" stop-opacity=".18"/>
 <stop offset="1" stop-color="#5aa9ff" stop-opacity="0"/>
</linearGradient>
<mask id="mDoppler" maskUnits="userSpaceOnUse" x="-420" y="-200" width="840" height="400"><rect x="-420" y="-200" width="840" height="400" fill="url(#doppler)"/></mask>
<mask id="mHalo" maskUnits="userSpaceOnUse" x="-140" y="-140" width="280" height="280"><rect x="-140" y="-140" width="280" height="280" fill="url(#haloFade)"/></mask>
<clipPath id="front"><path clip-rule="evenodd" d="M-700,-300H700V300H-700Z M-63,0A63,63 0 0 1 63,0Z"/></clipPath>
<clipPath id="frame"><rect width="1200" height="520" rx="18"/></clipPath>
<filter id="soft" x="-20%" y="-60%" width="140%" height="220%"><feGaussianBlur stdDeviation="1.1"/></filter>
<filter id="bloom" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="5"/></filter>
<filter id="jetBlur" x="-200%" y="-20%" width="500%" height="140%"><feGaussianBlur stdDeviation="6"/></filter>
</defs>''')
A('<g clip-path="url(#frame)">')
A(f'<rect width="{W}" height="{H}" fill="url(#sky)"/>')
A('<ellipse cx="230" cy="130" rx="420" ry="230" fill="url(#nebA)"/>')
A('<ellipse cx="1010" cy="400" rx="430" ry="240" fill="url(#nebB)"/>')

# stars
A('<g>')
for _ in range(280):
    x, y = random.uniform(0, W), random.uniform(0, H)
    r = random.choice([0.45, 0.55, 0.7, 0.7, 0.9, 1.1, 1.5])
    col = random.choice(["#ffffff", "#ffffff", "#cfe3ff", "#ffe9c9", "#bcd2ff"])
    op = random.uniform(0.35, 0.95)
    if random.random() < 0.22:
        d = random.uniform(2.5, 7)
        A(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{col}" opacity="{op:.2f}">'
          f'<animate attributeName="opacity" values="{op:.2f};{op * 0.2:.2f};{op:.2f}" dur="{d:.1f}s" '
          f'begin="-{random.uniform(0, d):.1f}s" repeatCount="indefinite"/></circle>')
    else:
        A(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{col}" opacity="{op:.2f}"/>')
A('</g>')

# the hole
A(f'<g transform="translate({CX} {CY}) rotate(-8)">')
A('<circle r="300" fill="url(#aura)"><animate attributeName="opacity" values=".8;1;.8" dur="7s" repeatCount="indefinite"/></circle>')
# relativistic jets
A('<g filter="url(#jetBlur)"><animate attributeName="opacity" values=".55;1;.55" dur="5s" repeatCount="indefinite"/>'
  '<path d="M-7,-60 L-26,-330 L26,-330 L7,-60Z" fill="url(#jet)"/>'
  '<path d="M-7,-60 L-26,-330 L26,-330 L7,-60Z" fill="url(#jet)" transform="scale(1 -1)"/></g>')
A(f'<circle r="{RS + 1}" fill="#000"/>')
A('<g mask="url(#mDoppler)">')
# lensed halo: light from the far side of the disk bent over and under the shadow
A('<g mask="url(#mHalo)"><g transform="translate(0 -3)">')
A('<circle r="128" fill="url(#haloGlow)"/>')
A('<g filter="url(#soft)">')
n = 13
for i in range(n):
    t = i / (n - 1)
    r = lerp(67, 116, t)
    A(ring(r, random.uniform(3, 5.5), heat(t * 0.75), lerp(0.85, 0.08, t ** 0.7), lerp(5, 13, t), 3, 6))
A('</g></g></g>')
# photon ring
A(f'<circle r="{RS + 2.5}" fill="none" stroke="#ffd9a0" stroke-width="5" opacity=".7" filter="url(#bloom)"/>')
A(f'<circle r="{RS + 2}" fill="none" stroke="#fffaf0" stroke-width="1.5" opacity=".95"/>')
# accretion disk, hidden where it passes behind the shadow
A('<g clip-path="url(#front)">')
A(f'<ellipse rx="{R_OUT}" ry="{R_OUT * TILT * 1.6:.1f}" fill="#ff8a3c" opacity=".35" filter="url(#bloom)"/>')
A(f'<g filter="url(#soft)"><g transform="scale(1 {TILT})">')
A(f'<circle r="{R_OUT}" fill="url(#diskGlow)"/>')
n = 46
for i in range(n):
    t = i / (n - 1)
    r = lerp(R_IN, R_OUT - 8, t ** 1.15)
    dur = 5.5 * (r / R_IN) ** 1.5            # Keplerian: inner orbits run faster
    A(ring(r, random.uniform(3.5, 8), heat(t), lerp(0.95, 0.22, t) * random.uniform(0.7, 1), dur))
# infalling matter spiralling in
pts = []
for k in range(241):
    u = k / 240
    r = lerp(R_OUT + 20, R_IN, u ** 0.8)
    a = -u * 2 * math.pi * 2.75
    pts.append(f"{r * math.cos(a):.1f},{r * math.sin(a):.1f}")
spiral = "M" + " L".join(pts)
for j in range(6):
    A(f'<circle r="3.2" fill="#fff8e6" opacity="0"><animateMotion dur="16s" begin="-{j * 16 / 6:.2f}s" '
      f'repeatCount="indefinite" path="{spiral}" keyPoints="0;1" keyTimes="0;1" keySplines=".5 0 .9 .5" calcMode="spline"/>'
      f'<animate attributeName="opacity" values="0;.95;.95;0" keyTimes="0;.15;.9;1" dur="16s" begin="-{j * 16 / 6:.2f}s" repeatCount="indefinite"/></circle>')
A('</g></g>')
A(f'<ellipse rx="{R_IN + 3}" ry="{(R_IN + 3) * TILT:.1f}" fill="none" stroke="#fffdf5" stroke-width="1.6" opacity=".85"/>')
A('</g></g></g>')

# HUD
F = "font-family=\"ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace\""
A(f'<g {F} fill="#9fd8ff" stroke="none">')
A('<g fill="none" stroke="#9fd8ff" stroke-opacity=".45" stroke-width="1.2">'
  '<path d="M28,52V28H52"/><path d="M1148,28H1172V52"/><path d="M28,468V492H52"/><path d="M1148,492H1172V468"/></g>')
A('<text x="64" y="50" font-size="12" letter-spacing="2.5" opacity=".75">OBJECT ASH-01 // KERR BLACK HOLE</text>')
A('<circle cx="1034" cy="46" r="3.5" fill="#ff7a59"><animate attributeName="opacity" values="1;.15;1" dur="1.6s" repeatCount="indefinite"/></circle>')
A('<text x="1136" y="50" font-size="12" letter-spacing="2.5" opacity=".75" text-anchor="end">LIVE FEED</text>')
A('<text x="600" y="455" font-size="30" letter-spacing="14" fill="#f4f8ff" text-anchor="middle" font-weight="600">ASHWANI JHA</text>')
A('<text x="600" y="482" font-size="12.5" letter-spacing="4" opacity=".8" text-anchor="middle">AI SUGGESTIONS REJECTED: MANY</text>')
A(f'<text x="64" y="476" font-size="11" letter-spacing="1.5" opacity=".6">CONTRIBUTIONS / 365D  {stat("total", "{:,}")}</text>')
A(f'<text x="64" y="492" font-size="11" letter-spacing="1.5" opacity=".6">CURRENT STREAK  {stat("streak")} D</text>')
A(f'<text x="1136" y="476" font-size="11" letter-spacing="1.5" opacity=".6" text-anchor="end">PEAK DAY  {stat("peak")}</text>')
A(f'<text x="1136" y="492" font-size="11" letter-spacing="1.5" opacity=".6" text-anchor="end">LAST SIGNAL  {stat("last")}</text>')
A('</g>')
A('</g></svg>')

open("blackhole.svg", "w").write("\n".join(out))
print("wrote blackhole.svg", sum(len(s) for s in out) // 1024, "KB")
