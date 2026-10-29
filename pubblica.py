"""Pubblica su Instagram i post in coda/ la cui ora è arrivata.
Ogni post è una cartella coda/AAAA-MM-GG-HHMM-nome/ con 01.jpg, 02.jpg... e didascalia.txt.
Ora = ora italiana (Europe/Rome). Dopo la pubblicazione la cartella va in pubblicati/."""
import os, sys, time, json, shutil, datetime, urllib.request, urllib.parse
from zoneinfo import ZoneInfo

TOKEN = os.environ["IG_TOKEN"]
REPO = os.environ["GITHUB_REPOSITORY"]
API = "https://graph.instagram.com/v23.0"
RAW = f"https://raw.githubusercontent.com/{REPO}/main"

def call(method, path, **params):
    params["access_token"] = TOKEN
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    req = urllib.request.Request(url, data=data, method="POST") if method == "POST" else urllib.request.Request(url + "?" + data.decode())
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Errore Instagram {e.code}: {e.read().decode()}")

def aspetta(cid):
    for _ in range(30):
        s = call("GET", cid, fields="status_code").get("status_code")
        if s == "FINISHED": return
        if s == "ERROR": raise SystemExit(f"Instagram non accetta il contenuto {cid}")
        time.sleep(5)
    raise SystemExit(f"Tempo scaduto per {cid}")

def pubblica(cartella):
    nome = os.path.basename(cartella)
    foto = sorted(f for f in os.listdir(cartella) if f.lower().endswith((".jpg", ".jpeg")))
    testo = open(os.path.join(cartella, "didascalia.txt"), encoding="utf-8").read().strip()
    urls = [f"{RAW}/coda/{urllib.parse.quote(nome)}/{f}" for f in foto]
    if len(urls) == 1:
        c = call("POST", "me/media", image_url=urls[0], caption=testo)["id"]
    else:
        figli = []
        for u in urls:
            figli.append(call("POST", "me/media", image_url=u, is_carousel_item="true")["id"])
        for f in figli: aspetta(f)
        c = call("POST", "me/media", media_type="CAROUSEL", children=",".join(figli), caption=testo)["id"]
    aspetta(c)
    pid = call("POST", "me/media_publish", creation_id=c)["id"]
    print(f"PUBBLICATO {nome} -> {pid}")
    return pid

def main():
    adesso = datetime.datetime.now(ZoneInfo("Europe/Rome"))
    fatti = []
    for nome in sorted(os.listdir("coda")):
        p = os.path.join("coda", nome)
        if not os.path.isdir(p): continue
        try:
            quando = datetime.datetime.strptime(nome[:15], "%Y-%m-%d-%H%M").replace(tzinfo=ZoneInfo("Europe/Rome"))
        except ValueError:
            continue
        if quando <= adesso:
            pubblica(p); fatti.append(nome)
    with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as o:
        o.write(f"fatti={' '.join(fatti)}\n")

if __name__ == "__main__":
    main()
