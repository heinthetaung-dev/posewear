# v10 post-build processing: hashed assets, static detail pages, SEO files, _headers (called by build.py)
import os, shutil, json, hashlib, base64, re, html as H
import seo

SITE = os.environ.get('POSEWEAR_SITE', 'https://posewear.pages.dev').rstrip('/')  # Update when deploying to custom domain
AH = os.environ.get('POSEWEAR_ASSET_HOST', '').rstrip('/')  # Asset host for split deployment (see AHOST in build.py)

def TU(p): return p if p.startswith('http') else (AH + '/' + p if AH else '/' + p)  # Thumbnail relative reference
def TS(p): return p if p.startswith('http') else (AH + '/' + p if AH else SITE + '/' + p)  # Thumbnail absolute reference (JSON-LD)

h8 = lambda b: hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()[:10]
LOGO = '<span class="mk"><svg viewBox="0 0 32 32" aria-hidden="true"><circle cx="16" cy="6.6" r="4" fill="currentColor"/><path d="M16 13.4 3.4 25.6h25.2z" fill="none" stroke="currentColor" stroke-width="3.4" stroke-linejoin="round"/></svg></span>'
E = lambda s: H.escape(str(s), quote=True)

CSS = '''body{margin:0;font:15px/1.7 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;color:#111;background:#fff}a{color:inherit}
header{display:flex;align-items:center;gap:10px;padding:14px 20px;border-bottom:1px solid #f0f0f0}header a{text-decoration:none;font-weight:700;display:flex;align-items:center;gap:8px}
.mk{width:26px;height:26px;color:#ff2442;display:grid;place-items:center}.mk svg{width:26px;height:26px}
main{max-width:1040px;margin:0 auto;padding:24px 20px;display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:32px}
@media(max-width:760px){main{grid-template-columns:1fr}}
.im img{width:100%;height:auto;border-radius:16px;background:#f5f5f5;display:block}
h1{font-size:24px;margin:0 0 6px}.mu{color:#666;font-size:13px}.bc{font-size:13px;color:#666;margin-bottom:12px}
.box{background:#f5f5f5;border-radius:14px;padding:14px 16px;margin:14px 0}.box small{color:#666}
.go{display:inline-block;background:#d81b3a;color:#fff;border-radius:999px;padding:10px 22px;text-decoration:none;font-weight:600;margin:6px 8px 6px 0}
.rel{grid-column:1/-1}.rel ul{list-style:none;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:12px}.rel img{width:100%;height:auto;border-radius:10px;background:#f5f5f5;display:block}.rel a{text-decoration:none;font-size:13px}
footer{text-align:center;color:#666;font-size:12px;padding:30px 20px;border-top:1px solid #f0f0f0}
h1{overflow-wrap:anywhere}
@media(prefers-color-scheme:dark){body{color:#eee;background:#111}header,footer{border-color:#262626}.mu,.bc,.box small,footer{color:#9a9a9a}.box{background:#1d1d1d}.im img,.rel img{background:#1d1d1d}.go[style]{background:#eee!important;color:#111!important}}
:root{color-scheme:light dark}'''


def run(D, PJ, CJ, AJ, RJ, DJ, DEPTH_ORIGINS, poses, PL, cos, acs, pors, R='assets-raw', AHOST=''):
    global AH, SITE
    if AHOST:
        AH = AHOST.rstrip('/')
    os.makedirs(f'{D}/assets', exist_ok=True)
    for f in os.listdir(f'{D}/assets'):
        os.remove(f'{D}/assets/{f}')
    A = {}
    def put(name, data):
        b = data.encode() if isinstance(data, str) else data
        base, ext = name.rsplit('.', 1)
        n = f'assets/{base}.{h8(b)}.{ext}'
        open(f'{D}/{n}', 'wb').write(b)
        A[name] = n
        return n

    put('poses.json', PJ)
    put('costumes.json', CJ)
    put('anime.json', AJ)
    put('portraits.json', RJ)
    put('depths.json', DJ)
    for f in ['style.css', 'zip.js', 'extras.js', 'studio.js']:
        put(f, open(f'src/{f}', 'rb').read())
    app = open('src/app.js').read()
    if AH:
        app = app.replace("const AH='';", f"const AH='{AH}/';")
    app = app.replace("'poses.json'", "'/" + A['poses.json'] + "'").replace("'costumes.json'", "'/" + A['costumes.json'] + "'").replace("'anime.json'", "'/" + A['anime.json'] + "'").replace("'portraits.json'", "'/" + A['portraits.json'] + "'").replace("'depths.json'", "'/" + A['depths.json'] + "'")
    put('app.js', app)
    VER = 'posewear-v10-' + h8(''.join(A.values()))
    idx = open('src/index.html').read()
    for f in ['style.css', 'app.js', 'zip.js', 'extras.js', 'studio.js']:
        idx = idx.replace(f'"{f}"', f'"/{A[f]}"')
    idx = idx.replace('href="poses.json"', f'href="/{A["poses.json"]}"')
    open(f'{D}/index.html', 'w').write(idx)
    for f in ['style.css', 'app.js', 'zip.js', 'extras.js', 'studio.js']:
        if os.path.exists(f'{D}/{f}'):
            os.remove(f'{D}/{f}')
    sw = open('src/sw.js').read().replace("const V='posewear-v9'", f"const V='{VER}'")
    sw = sw.replace("['./','index.html','style.css','app.js','studio.js','extras.js','zip.js','favicon.svg']", json.dumps(['/', '/favicon.svg'] + ['/' + A[f] for f in ['style.css', 'app.js', 'studio.js', 'extras.js', 'zip.js', 'poses.json', 'depths.json']]))
    open(f'{D}/sw.js', 'w').write(sw)
    inl = re.findall(r'<script>(.*?)</script>', idx, re.S)
    SH = ' '.join("'sha256-" + base64.b64encode(hashlib.sha256(x.encode()).digest()).decode() + "'" for x in inl)
    # ---------- Static detail pages ----------
    for d in ['pose', 'costume', 'anime', 'portrait']:
        if os.path.exists(f'{D}/{d}'):
            shutil.rmtree(f'{D}/{d}')
    open(f'{D}/404.html', 'w').write(f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Page Not Found | PoseWear</title><meta name="robots" content="noindex"><link rel="icon" href="/favicon.svg" type="image/svg+xml"><style>{CSS}
.nf{{max-width:480px;margin:12vh auto;text-align:center;padding:0 20px}}.nf b{{font-size:64px;color:#d81b3a;display:block;line-height:1}}</style></head><body><header><a href="/">{LOGO}PoseWear</a></header>
<div class="nf"><b>404</b><h1>Page Not Found</h1><p class="mu">The link might be broken or the content has moved.</p><a class="go" href="/">Go Home</a><a class="go" style="background:#111" href="/#costume">Browse Costumes</a></div></body></html>''')
    _IMG = " ".join(["'self'", "data:", "blob:"] + list(DEPTH_ORIGINS) + ([AH] if AH else []))
    CSP = ("default-src 'self'; script-src 'self' " + SH + "; style-src 'self' 'unsafe-inline'; img-src " + _IMG + "; font-src 'self' data:; "
     "connect-src 'self' data: blob: https://api.openai.com https://generativelanguage.googleapis.com https://*.volces.com https://*.bytepluses.com https://oaidalleapiprodscus.blob.core.windows.net https://*.googleusercontent.com; "
     "worker-src 'self'; manifest-src 'self'; media-src 'self' blob:; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; upgrade-insecure-requests")
    IMM = '  Cache-Control: public, max-age=31536000, immutable\n'
    open(f'{D}/_headers', 'w').write(f'''/*
  Content-Security-Policy: {CSP}
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  X-Frame-Options: DENY
  Strict-Transport-Security: max-age=31536000; includeSubDomains
  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()
  Cross-Origin-Opener-Policy: same-origin
/assets/*
{IMM}/p/*
{IMM}/c/*
{IMM}/a/*
{IMM}/r/*
{IMM}/o/*
{IMM}/icon-*
  Cache-Control: public, max-age=86400
/og.png
  Cache-Control: public, max-age=86400
/sw.js
  Cache-Control: no-cache
/
  Cache-Control: public, max-age=0, must-revalidate
/index.html
  Cache-Control: public, max-age=0, must-revalidate
/pose/*
  Cache-Control: public, max-age=600
/costume/*
  Cache-Control: public, max-age=600
/anime/*
  Cache-Control: public, max-age=600
/portrait/*
  Cache-Control: public, max-age=600
''')
    seo.run(D=D, R=R, poses=poses, PL=PL, cos=cos, acs=acs, pors=pors, SITE=SITE, AH=AH)
