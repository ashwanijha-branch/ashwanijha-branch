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
RS = 62                       # apparent shadow radius, px
BCRIT = 1.5 * math.sqrt(3)    # critical impact parameter, in Schwarzschild radii
S = RS / BCRIT                # px per Schwarzschild radius
R_IN, R_OUT = 3.0, 14.0       # disk extent, in Schwarzschild radii
ELEV = math.radians(7)        # camera elevation above the disk plane

def lerp(a, b, t): return a + (b - a) * t

STOPS = [(0.0, (255, 246, 222)), (0.18, (255, 208, 128)), (0.42, (255, 140, 60)),
         (0.72, (190, 62, 14)), (1.0, (84, 22, 10))]

def heat(t):
    for (t0, c0), (t1, c1) in zip(STOPS, STOPS[1:]):
        if t <= t1:
            k = (t - t0) / (t1 - t0)
            return "#%02x%02x%02x" % tuple(round(lerp(a, b, k)) for a, b in zip(c0, c1))
    return "#54160a"

def dashes(n):
    """Random dash pattern summing to 1000 (paths use pathLength=1000)."""
    parts = [random.uniform(0.4, 1.6) for _ in range(2 * n)]
    k = 1000 / sum(parts)
    return " ".join(f"{p * k:.1f}" for p in parts)

# ---- gravitational lensing -------------------------------------------------
# A light ray around a non-rotating hole stays in a plane and obeys
# u'' = -u + 1.5 u^2 with u = 1/r. Integrate it once per impact parameter b,
# then ask where each point of the disk appears on the image plane.
NPHI = 1440
DPHI = 2 * math.pi / NPHI

def orbit(b):
    u, v, us, done = 0.0, 1.0 / b, [0.0], None
    f = lambda u: -u + 1.5 * u * u
    for _ in range(NPHI):
        if done is None:
            k1u, k1v = v, f(u)
            k2u, k2v = v + 0.5 * DPHI * k1v, f(u + 0.5 * DPHI * k1u)
            k3u, k3v = v + 0.5 * DPHI * k2v, f(u + 0.5 * DPHI * k2u)
            k4u, k4v = v + DPHI * k3v, f(u + DPHI * k3u)
            u += DPHI * (k1u + 2 * k2u + 2 * k3u + k4u) / 6
            v += DPHI * (k1v + 2 * k2v + 2 * k3v + k4v) / 6
            if u >= 1.0: done = 2.0        # fell through the horizon
            elif u <= 0.0: done = -1.0     # escaped to infinity
        us.append(u if done is None else done)
    return us

def geom(a, b, n): return [a * (b / a) ** (i / (n - 1)) for i in range(n)]
BS = sorted([0.05 + i * 2.45 / 60 for i in range(60)] + [BCRIT - d for d in geom(1e-4, 0.09, 24)]
            + [BCRIT + d for d in geom(1e-5, 0.5, 40)] + geom(3.12, 60, 90))
ORBITS = [orbit(b) for b in BS]
FIRST_OUTSIDE = next(i for i, b in enumerate(BS) if b > BCRIT)

def radius_at(us, phi):
    j = phi / DPHI
    i = min(int(j), NPHI - 1)
    a, b = us[i], us[i + 1]
    if a < 0 or b < 0: return math.inf
    if a >= 2 or b >= 2: return 0.0
    u = a + (b - a) * (j - i)
    return 1 / u if u > 1e-9 else math.inf

def invert(f, r, start=0):
    """Impact parameter at which the ray reaches radius r (f is increasing in b)."""
    for i in range(start, len(BS) - 1):
        if f[i] <= r <= f[i + 1]:
            if math.isinf(f[i + 1]) or f[i + 1] == f[i]: return BS[i]
            return BS[i] + (BS[i + 1] - BS[i]) * (r - f[i]) / (f[i + 1] - f[i])
    return BS[start] if r < f[start] else BS[-1]

def view(psi):
    """For disk azimuth psi: image-plane direction and the radius profiles of both images."""
    cg = math.sin(psi) * math.cos(ELEV)
    g = math.acos(max(-1, min(1, cg)))
    sg = math.sin(g)
    dx, dy = math.cos(psi) / sg, math.sin(psi) * math.sin(ELEV) / sg   # dy is down the screen
    direct = [radius_at(o, g) for o in ORBITS]
    ghost = [radius_at(o, 2 * math.pi - g) if i >= FIRST_OUTSIDE else 0.0 for i, o in enumerate(ORBITS)]
    return dx, dy, direct, ghost

# Sample evenly in screen angle, not disk azimuth: seen nearly edge-on, even azimuth steps
# would bunch up at the sides and leave the arc over the top with almost no points.
NPSI = 240
def azimuth(alpha): return math.atan2(math.sin(alpha) / math.sin(ELEV), math.cos(alpha))
VIEWS = [view(azimuth(-2 * math.pi * (k + 0.37) / NPSI)) for k in range(NPSI)]   # runs in the direction of rotation

def direct_curve(r):      # the disk as seen directly
    return [(invert(d, r) * dx * S, invert(d, r) * dy * S) for dx, dy, d, _ in VIEWS]
def ghost_curve(r):       # second image: light that went around the far side of the hole
    return [(-invert(g, r, FIRST_OUTSIDE) * dx * S, -invert(g, r, FIRST_OUTSIDE) * dy * S) for dx, dy, _, g in VIEWS]
def path(pts): return "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z"

def streak(pts, width, color, opacity, dur, n):
    off = random.uniform(0, 1000)
    return (f'<path d="{path(pts)}" pathLength="1000" fill="none" stroke="{color}" stroke-width="{width:.1f}" '
            f'stroke-opacity="{opacity:.2f}" stroke-dasharray="{dashes(n)}" stroke-dashoffset="{off:.0f}">'
            f'<animate attributeName="stroke-dashoffset" from="{off:.0f}" to="{off - 1000:.0f}" dur="{dur:.1f}s" '
            f'repeatCount="indefinite"/></path>')

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
<linearGradient id="doppler" gradientUnits="userSpaceOnUse" x1="-380" y1="0" x2="380" y2="0">
 <stop offset="0" stop-color="#fff"/><stop offset=".45" stop-color="#ddd"/><stop offset="1" stop-color="#7a7a7a"/>
</linearGradient>
<linearGradient id="jet" x1="0" y1="1" x2="0" y2="0">
 <stop offset="0" stop-color="#9fd8ff" stop-opacity=".55"/><stop offset=".4" stop-color="#5aa9ff" stop-opacity=".18"/>
 <stop offset="1" stop-color="#5aa9ff" stop-opacity="0"/>
</linearGradient>
<mask id="mDoppler" maskUnits="userSpaceOnUse" x="-420" y="-260" width="840" height="520"><rect x="-420" y="-260" width="840" height="520" fill="url(#doppler)"/></mask>
<clipPath id="frame"><rect width="1200" height="520" rx="18"/></clipPath>
<filter id="soft" x="-20%" y="-60%" width="140%" height="220%"><feGaussianBlur stdDeviation="1.1"/></filter>
<filter id="smooth" x="-10%" y="-20%" width="120%" height="140%"><feGaussianBlur stdDeviation="1.6"/></filter>
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
A('<g filter="url(#jetBlur)"><animate attributeName="opacity" values=".55;1;.55" dur="5s" repeatCount="indefinite"/>'
  '<path d="M-7,-60 L-26,-330 L26,-330 L7,-60Z" fill="url(#jet)"/>'
  '<path d="M-7,-60 L-26,-330 L26,-330 L7,-60Z" fill="url(#jet)" transform="scale(1 -1)"/></g>')
A(f'<circle r="{RS}" fill="#000"/>')

def radii(n): return [lerp(R_IN, R_OUT, (i / (n - 1)) ** 1.15) for i in range(n)]
def tt(r): return (r - R_IN) / (R_OUT - R_IN)

def glow(curve, n):
    """Filled bands between successive rings: the continuous glow under the streaks."""
    rs, parts = radii(n), []
    for a, b in zip(rs, rs[1:]):
        t = tt((a + b) / 2)
        parts.append(f'<path fill-rule="evenodd" d="{path(curve(a)[::2])}{path(curve(b)[::2])}" '
                     f'fill="{heat(0.12 + t * 0.88)}" fill-opacity="{0.78 * (1 - t) ** 1.2:.2f}"/>')
    return "".join(parts)

A('<g mask="url(#mDoppler)">')
A(f'<g id="ghost" opacity=".8">{glow(ghost_curve, 6)}</g>')
A(f'<g id="disk" filter="url(#smooth)">{glow(direct_curve, 20)}</g>')
A('<g filter="url(#bloom)" opacity=".6"><use href="#ghost"/><use href="#disk"/></g>')
A('<g filter="url(#soft)">')
for r in radii(7):                       # second image, hugging the shadow
    t = tt(r)
    A(streak(ghost_curve(r), random.uniform(1.2, 2.0), heat(t * 0.4), lerp(0.8, 0.2, t),
             5.5 * (r / R_IN) ** 1.5, random.randint(3, 6)))
A('<use href="#disk"/>')                 # the direct disk hides the second image where they overlap
for r in radii(26):
    t = tt(r)
    A(streak(direct_curve(r), random.uniform(1.8, 3.6), heat(t * 0.55), lerp(0.9, 0.3, t) * random.uniform(0.6, 1),
             5.5 * (r / R_IN) ** 1.5, random.randint(4, 9)))
A('</g>')
A(f'<circle r="{RS + 0.5}" fill="none" stroke="#ffd9a0" stroke-width="4" opacity=".55" filter="url(#bloom)"/>')
A(f'<circle r="{RS}" fill="none" stroke="#fffaf0" stroke-width="1.1" opacity=".9"/>')
A(f'<path d="{path(direct_curve(R_IN + 0.05))}" fill="none" stroke="#fffdf5" stroke-width="1.4" opacity=".8"/>')
# infalling matter spiralling in, lensed like everything else
pts = []
for k in range(201):
    w = k / 200
    r, psi = lerp(R_OUT + 0.5, R_IN + 0.1, w ** 0.8), -w * 2 * math.pi * 2.75 + 1e-4
    dx, dy, d, _ = view(psi)
    b = invert(d, r)
    pts.append(f"{b * dx * S:.1f},{b * dy * S:.1f}")
spiral = "M" + " L".join(pts)
for jdx in range(6):
    A(f'<circle r="1.7" fill="#fff8e6" opacity="0"><animateMotion dur="16s" begin="-{jdx * 16 / 6:.2f}s" '
      f'repeatCount="indefinite" path="{spiral}"/>'
      f'<animate attributeName="opacity" values="0;.95;.95;0" keyTimes="0;.15;.9;1" dur="16s" begin="-{jdx * 16 / 6:.2f}s" repeatCount="indefinite"/></circle>')
A('</g></g>')

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
