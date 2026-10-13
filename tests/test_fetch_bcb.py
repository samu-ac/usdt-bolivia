# Ejecuta fetch_prices.py en copias temporales: éxito real, fallo de officialRate con respaldo, y sin dato previo.
# Uso: python tests/test_fetch_bcb.py   (requiere red para la API DolarBlueBolivia; no modifica data/)
import json, os, shutil, subprocess, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = r'''
import sys, urllib.request
mode = sys.argv[1]
_orig = urllib.request.urlopen
def fake(req, *a, **k):
    url = req.full_url if hasattr(req, "full_url") else req
    if "dolarbluebolivia" not in url or (mode != "ok" and "officialRate" in url):
        raise OSError("simulado: sin red para " + url)
    return _orig(req, *a, **k)
urllib.request.urlopen = fake
exec(compile(open("fetch_prices.py", encoding="utf-8").read(), "fetch_prices.py", "exec"))
'''

def run(mode, drop_bcb=False):
    d = tempfile.mkdtemp()
    shutil.copy(os.path.join(REPO, "fetch_prices.py"), d)
    shutil.copytree(os.path.join(REPO, "data"), os.path.join(d, "data"))
    pj = os.path.join(d, "data", "prices.json")
    before = json.load(open(pj, encoding="utf-8"))
    if drop_bcb:
        before.pop("bcb", None)
        json.dump(before, open(pj, "w", encoding="utf-8"))
    open(os.path.join(d, "runner.py"), "w").write(RUNNER)
    r = subprocess.run([sys.executable, "runner.py", mode], cwd=d, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-2000:]
    after = json.load(open(pj, encoding="utf-8"))["bcb"]
    shutil.rmtree(d)
    return before.get("bcb"), after

prev, bcb = run("ok")
assert float(bcb["officialBuy"]) > 0 and bcb["source"] == "api_dbb_officialRate" and bcb["fetchedAt"], bcb
print("éxito   :", bcb)

prev, bcb = run("fail")
assert bcb["officialBuy"] == prev["officialBuy"] and bcb.get("fetchedAt") == prev.get("fetchedAt"), (prev, bcb)
assert bcb.get("source") == prev.get("source"), bcb  # no se inventa procedencia
print("respaldo:", bcb)

prev, bcb = run("fail", drop_bcb=True)
assert prev is None and bcb["officialBuy"] is None and "source" not in bcb, bcb
print("sin dato:", bcb)
print("OK")
