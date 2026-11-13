#!/usr/bin/env python3
"""presencia-web · diagnostico tecnico de la web de un negocio.

Mide 13 comprobaciones sobre una web publica y devuelve una nota sobre 100,
mas los tres fallos que mas cuestan. Sin dependencias, sin claves, sin coste.

    python3 presencia_web.py https://ejemplo.es
    python3 presencia_web.py https://ejemplo.es --html informe.html

Licencia Apache 2.0. Autor: Kelwin Correa.
"""
import sys, os, json, re, html, subprocess, tempfile, urllib.parse

VERSION = "1.0"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
LIMITE = 25


def descarga(url, timeout=LIMITE):
    """Descarga con curl.

    urllib provoca RemoteDisconnected en servidores con WAF que cierran la
    conexion sin cabeceras completas: eso da falsos positivos de 'web caida'
    sobre webs que responden 200. Comprobado a mano.
    """
    destino = tempfile.mktemp(suffix=".html")
    base = ["curl", "-sS", "-L", "--max-time", str(timeout), "-A", UA,
            "-H", "Accept: text/html,application/xhtml+xml,*/*;q=0.8",
            "-H", "Accept-Language: es-ES,es;q=0.9"]
    fmt = "%{http_code}|%{time_total}|%{size_download}|%{url_effective}|%{ssl_verify_result}"

    def intento(extra):
        r = subprocess.run(base + extra + ["-o", destino, "-w", fmt, url],
                           capture_output=True, text=True, timeout=timeout + 10)
        campos = (r.stdout or "").strip().split("|")
        if len(campos) < 5:
            return None
        return {"status": int(campos[0] or 0), "segundos": round(float(campos[1] or 0), 2),
                "bytes": int(campos[2] or 0), "url_final": campos[3],
                "tls_ok": campos[4].strip() in ("0", ""),
                "error_curl": (r.stderr or "").strip()[:120]}

    datos = intento([])
    if datos is None or datos["status"] == 0:
        datos = intento(["--http1.1"]) or datos

    texto = ""
    try:
        with open(destino, "rb") as f:
            texto = f.read(900000).decode("utf-8", "ignore")
    except Exception:
        pass
    finally:
        try:
            os.remove(destino)
        except Exception:
            pass

    if datos is None:
        return {"ok": False, "status": None, "segundos": None, "kb": None,
                "html": "", "tls_ok": None, "error": "curl no disponible"}
    ok = 200 <= datos["status"] < 400
    return {"ok": ok, "status": datos["status"], "segundos": datos["segundos"],
            "kb": round(datos["bytes"] / 1024, 1), "html": texto,
            "tls_ok": datos["tls_ok"],
            "error": None if ok else (f"HTTP {datos['status']}" if datos["status"]
                                      else (datos["error_curl"] or "sin respuesta"))}


def dns(nombre, tipo):
    try:
        r = subprocess.run(["host", "-t", tipo, nombre], capture_output=True,
                           text=True, timeout=8)
        return r.stdout
    except Exception:
        return ""


def analiza(url):
    r = descarga(url)
    h = r.get("html", "") or ""
    bajo = h.lower()
    plano = re.sub(r"<script.*?</script>|<style.*?</style>", " ", h, flags=re.S | re.I)
    plano = re.sub(r"<[^>]+>", " ", plano)
    imgs = re.findall(r"<img[^>]*>", h, re.I)
    mt = re.search(r"<title[^>]*>(.*?)</title>", h, re.S | re.I)

    d = {
        "url": url, "status": r["status"], "segundos": r["segundos"], "kb": r.get("kb"),
        "tls_ok": r["tls_ok"], "error": r["error"],
        "viewport": bool(re.search(r'name=["\']viewport', h, re.I)),
        "title": mt.group(1).strip()[:120] if mt else "",
        "meta_desc": bool(re.search(r'name=["\']description["\'][^>]*content=["\'][^"\']+', h, re.I)),
        "len_telefonos": len(re.findall(r"href=[\"']tel:", h, re.I)),
        "whatsapp": bool(re.search(r"wa\.me|api\.whatsapp\.com", h, re.I)),
        "formularios": len(re.findall(r"<form", h, re.I)),
        "palabras": len(re.findall(r"\b\w{2,}\b", plano)),
        "h1": len(re.findall(r"<h1", h, re.I)),
        "aviso_legal": bool(re.search(r"aviso legal|informacion legal|datos identificativos", bajo)),
        "privacidad": "privacidad" in bajo,
        "cookies": "cookie" in bajo,
        "imgs": len(imgs),
        "imgs_sin_alt": sum(1 for i in imgs if "alt=" not in i.lower()),
        "cta": bool(re.search(r"reservar|pedir cita|pide cita|solicitar cita|contactar|llamar ahora|solicita", bajo)),
        "schema_local": bool(re.search(
            r'"@type"\s*:\s*"(LocalBusiness|Dentist|MedicalBusiness|Store|Restaurant|'
            r'HealthAndBeautyBusiness)"', h)),
    }
    dom = re.sub(r"^www\.", "", (urllib.parse.urlparse(url).netloc or "").split(":")[0])
    d["dominio"] = dom
    d["spf"] = "SI" if "v=spf1" in dns(dom, "TXT") else "NO"
    d["dmarc"] = "SI" if "v=DMARC1" in dns("_dmarc." + dom, "TXT") else "NO"

    p, fallos = 0, []
    if r["ok"] and r["tls_ok"]:
        p += 15
    elif not r["ok"]:
        fallos.append(("La web no responde",
                       "Quien entra ve un error. La venta se pierde antes de leer nada.", 45))
    else:
        fallos.append(("Certificado no valido",
                       "El navegador avisa de que el sitio no es seguro y mucha gente se va.", 30))
    if r["ok"] and (r["segundos"] or 99) < 2.5:
        p += 10
    elif r["ok"]:
        fallos.append((f"Tarda {r['segundos']} s en cargar",
                       "Por encima de 2,5 s se va buena parte de las visitas.", 20))
    if d["viewport"]:
        p += 15
    else:
        fallos.append(("No esta adaptada al movil",
                       "En el telefono se ve como una web de ordenador, y de ahi llega la mayoria.", 35))
    if d["len_telefonos"] or d["whatsapp"]:
        p += 10
    else:
        fallos.append(("Sin telefono ni WhatsApp pulsable",
                       "Quien decide llamar tiene que copiar el numero a mano. Muchos no lo hacen.", 15))
    if d["title"] and d["meta_desc"]:
        p += 8
    else:
        fallos.append(("Sin titulo o descripcion",
                       "Google no sabe de que va el negocio y no lo muestra bien.", 10))
    if d["aviso_legal"]:
        p += 7
    else:
        fallos.append(("Sin aviso legal",
                       "La ley de servicios digitales obliga a identificarse. Es sancionable y no cuesta nada arreglarlo.", 12))
    if d["privacidad"]:
        p += 5
    else:
        fallos.append(("Sin politica de privacidad",
                       "Si la web recoge cualquier dato sin politica, incumple el reglamento de proteccion de datos.", 10))
    if d["cookies"]:
        p += 5
    else:
        fallos.append(("Sin aviso de cookies",
                       "Obligatorio si hay analitica o pixeles. Es de las sanciones mas frecuentes a pymes.", 8))
    if d["h1"] == 1:
        p += 5
    if d["palabras"] >= 300:
        p += 10
    else:
        fallos.append((f"Solo {d['palabras']} palabras de contenido",
                       "Casi no hay texto que Google pueda leer, asi que no aparece en las busquedas.", 15))
    if d["cta"]:
        p += 5
    else:
        fallos.append(("No hay una accion clara",
                       "Se visita la web y no se sabe si hay que llamar, escribir o reservar.", 12))
    if d["schema_local"]:
        p += 5
    if d["imgs"] and d["imgs_sin_alt"] / max(1, d["imgs"]) > 0.4:
        fallos.append((f"{d['imgs_sin_alt']} de {d['imgs']} imagenes sin describir",
                       "Google no sabe que muestran y no las usa para posicionar en busquedas locales.", 5))

    d["nota"] = max(0, min(100, p))
    d["fallos"] = sorted(fallos, key=lambda x: -x[2])[:3]
    d["no_comprobado"] = [
        "La ficha de Google: si existe, cuantas resenas tiene y con que nota",
        "La posicion real en Google al buscar lo que vende",
        "Si el telefono lo coge alguien",
    ]
    return d


def informe_html(d, salida):
    color = "#b3261e" if d["nota"] < 50 else ("#b26a00" if d["nota"] < 75 else "#1b6e3c")
    filas = "".join(f"<tr><td>{html.escape(f[0])}</td><td>{html.escape(f[1])}</td></tr>"
                    for f in d["fallos"]) or "<tr><td colspan='2'>Sin fallos graves medidos.</td></tr>"
    nc = "".join(f"<li>{html.escape(x)}</li>" for x in d["no_comprobado"])
    doc = f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Diagnostico de presencia web · {html.escape(d['dominio'])}</title>
<style>
body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#f6f7f9;color:#14181f}}
.wrap{{max-width:760px;margin:0 auto;padding:32px 20px 60px}}
h1{{font-size:22px;margin:0 0 4px}} .sub{{color:#5b6472;font-size:14px;margin-bottom:24px}}
.nota{{display:flex;align-items:center;gap:18px;background:#fff;border:1px solid #e3e6eb;border-radius:14px;padding:22px;margin-bottom:24px}}
.num{{font-size:56px;font-weight:700;color:{color};line-height:1}}
h2{{font-size:16px;margin:28px 0 10px}}
table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e3e6eb;border-radius:12px;overflow:hidden}}
th,td{{text-align:left;padding:12px 14px;border-bottom:1px solid #eef0f3;font-size:14px;vertical-align:top}}
th{{background:#f0f2f5;font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:#5b6472}}
ul{{background:#fff;border:1px solid #e3e6eb;border-radius:12px;padding:14px 14px 14px 34px;font-size:14px}}
.datos{{font-size:13px;color:#5b6472;margin-top:18px}}
</style></head><body><div class="wrap">
<h1>Diagnostico de presencia web</h1>
<div class="sub">{html.escape(d['url'])} · medido automaticamente</div>
<div class="nota"><div class="num">{d['nota']}</div>
<div><strong>Sobre 100.</strong><br>Medido, no estimado. Cada punto sale de una comprobacion real sobre la web.</div></div>
<h2>Los tres fallos que mas cuestan</h2>
<table><tr><th>Fallo</th><th>Que cuesta</th></tr>{filas}</table>
<h2>Lo que esta herramienta no mira</h2>
<ul>{nc}</ul>
<div class="datos">HTTP {d.get('status')}, {d.get('segundos')} s, {d.get('kb')} KB,
movil {'si' if d.get('viewport') else 'no'}, SPF {d.get('spf')}, DMARC {d.get('dmarc')}.</div>
</div></body></html>"""
    with open(salida, "w", encoding="utf-8") as f:
        f.write(doc)
    return salida


def main():
    args = [a for a in sys.argv[1:]]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return
    url = args[0]
    if not url.startswith("http"):
        url = "https://" + url
    d = analiza(url)
    print(f"\n{d['dominio']}  ->  {d['nota']}/100\n")
    print(f"HTTP {d['status']} · {d['segundos']} s · {d['kb']} KB · "
          f"movil {'si' if d['viewport'] else 'no'} · "
          f"telefono {'si' if d['len_telefonos'] else 'no'}\n")
    print("Los tres fallos que mas cuestan:")
    for f in d["fallos"]:
        print(f"  · {f[0]}: {f[1]}")
    if not d["fallos"]:
        print("  · Ningun fallo grave en lo que se mide aqui.")
    if "--html" in args:
        salida = args[args.index("--html") + 1]
        informe_html(d, salida)
        print(f"\nInforme HTML: {salida}")
    if "--json" in args:
        print(json.dumps(d, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
