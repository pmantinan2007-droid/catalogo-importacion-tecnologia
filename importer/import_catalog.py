#!/usr/bin/env python3
"""Importador inicial basado en JSON-LD/Open Graph. Ajustar por proveedor tras validar."""
import json, os, re, hashlib, html
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "importer" / "providers.json"
OUTPUT = ROOT / "data" / "products.json"
ALLOWED = re.compile(r"(iphone|smartphone|celular|phone|galaxy|xiaomi|motorola|iphone|playstation|xbox|nintendo|console|consola|gaming|gamer|gamepad|joystick|smartwatch|smart watch|apple watch|galaxy watch|auricular|headphone|headset|parlante|speaker|jbl|audio|cable|cargador|adaptador|power bank|usb|tablet|notebook|laptop|ssd|memoria ram|placa de video|teclado|mouse|mouse gamer|webcam|dji|drone)", re.I)
SKIP = re.compile(r"(perfume|bebida|alimento|suplemento|cigarrillo|tabaco|ropa|calzado|maquillaje|mueble)", re.I)

def abs_url(url, base):
    if not url: return ""
    return urljoin(base, html.unescape(url.strip()))

def parse_price(value):
    if value is None: return None
    if isinstance(value, (int,float)): return float(value)
    s = re.sub(r"[^\d,.\-]", "", str(value)).strip()
    if not s: return None
    # Product JSON-LD often has decimal-dot prices; localized text is handled conservatively.
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."): s = s.replace(".", "").replace(",", ".")
        else: s = s.replace(",", "")
    elif "," in s:
        tail=s.rsplit(",",1)[-1]
        s=s.replace(",", ".") if len(tail) in (1,2) else s.replace(",", "")
    try: return float(s)
    except ValueError: return None

def jsonld_products(soup, page_url, provider):
    out=[]
    for script in soup.select('script[type="application/ld+json"]'):
        try: data=json.loads(script.string or script.get_text())
        except Exception: continue
        stack=data if isinstance(data,list) else [data]
        while stack:
            obj=stack.pop()
            if isinstance(obj,list): stack.extend(obj); continue
            if not isinstance(obj,dict): continue
            if "@graph" in obj: stack.append(obj["@graph"])
            typ=obj.get("@type",[])
            if isinstance(typ,str): typ=[typ]
            if any(t.lower()=="product" for t in typ):
                offers=obj.get("offers",{})
                if isinstance(offers,list): offers=offers[0] if offers else {}
                if not isinstance(offers,dict): offers={}
                price=parse_price(offers.get("price") or offers.get("lowPrice"))
                currency=offers.get("priceCurrency") or ""
                img=obj.get("image","")
                if isinstance(img,list): img=img[0] if img else ""
                name=(obj.get("name") or "").strip()
                if not name: continue
                out.append({
                    "name":name,"brand":brand_name(obj.get("brand")),"description":strip_html(obj.get("description","")),
                    "image_url":abs_url(img,page_url),"source_url":abs_url(obj.get("url") or page_url,page_url),
                    "raw_price":price,"raw_currency":currency,"provider":provider
                })
    return out

def brand_name(value):
    if isinstance(value,dict): return str(value.get("name",""))
    return str(value or "")

def strip_html(value):
    return re.sub(r"\s+"," ",BeautifulSoup(str(value), "html.parser").get_text(" ",strip=True)).strip()[:1200]

def parse_open_graph(soup, page_url, provider):
    title=(soup.select_one('meta[property="og:title"]') or {}).get("content","")
    image=(soup.select_one('meta[property="og:image"]') or {}).get("content","")
    description=(soup.select_one('meta[property="og:description"]') or {}).get("content","")
    # OG price tags appear on product detail pages, not reliably on category listings.
    price=(soup.select_one('meta[property="product:price:amount"]') or {}).get("content")
    currency=(soup.select_one('meta[property="product:price:currency"]') or {}).get("content","")
    if title and price:
        return [{"name":title,"brand":"","description":strip_html(description),"image_url":abs_url(image,page_url),
                 "source_url":page_url,"raw_price":parse_price(price),"raw_currency":currency,"provider":provider}]
    return []

def categorize(p):
    s=" ".join([p.get("name",""),p.get("brand",""),p.get("description","")]).lower()
    if re.search(r"playstation|xbox|nintendo|consola|gaming|gamer|gamepad|joystick|videojuego",s): return "Gaming"
    if re.search(r"smartwatch|smart watch|apple watch|galaxy watch|reloj inteligente",s): return "Smartwatches"
    if re.search(r"iphone|smartphone|celular|galaxy s\d|redmi note|moto g\d",s): return "Celulares"
    if re.search(r"auricular|headphone|headset|parlante|speaker|soundbar|audio|jbl",s): return "Audio"
    if re.search(r"cable|cargador|adaptador|funda|power bank|memoria|pendrive|usb|accesorio",s): return "Accesorios"
    if re.search(r"tablet|notebook|laptop|ssd|placa de video|memoria ram|teclado|mouse|webcam|monitor|dji|drone",s): return "Electrónica portátil"
    return ""

def to_usd(price, currency):
    if price is None: return None
    c=(currency or "").upper().strip()
    if c in ("USD","US$","$US"): return float(price)
    # Guaraníes and ARS cannot be converted safely without a verified exchange-rate source.
    # Do not infer currency from the symbol '$' alone.
    return None

def product_id(provider, url, name):
    return hashlib.sha1((provider+"|"+(url or name)).encode("utf-8")).hexdigest()[:16]

def main():
    config=json.loads(CONFIG.read_text(encoding="utf-8"))
    session=requests.Session()
    session.headers.update({"User-Agent":config.get("user_agent","Mozilla/5.0 (compatible; CatalogImporter/0.1)")})
    timeout=int(config.get("timeout_seconds",20))
    markup=float(config.get("markup_percent",40))
    ars_per_usd=parse_price(os.environ.get(config.get("ars_per_usd_env","ARS_PER_USD")))
    results={}
    failures=[]
    for provider in config["providers"]:
        if not provider.get("enabled",True): continue
        for page_url in provider.get("category_urls",[])[:int(config.get("max_pages",1))]:
            try:
                response=session.get(page_url,timeout=timeout)
                response.raise_for_status()
                soup=BeautifulSoup(response.text,"html.parser")
                found=jsonld_products(soup,page_url,provider["name"])
                if not found: found=parse_open_graph(soup,page_url,provider["name"])
                if not found:
                    failures.append({"provider":provider["name"],"url":page_url,"error":"No se detectaron productos JSON-LD/OG. Requiere integración específica."})
                for item in found:
                    name=item.get("name","").strip()
                    combined=name+" "+item.get("description","")
                    if not ALLOWED.search(combined) or SKIP.search(combined): continue
                    cat=categorize(item)
                    if not cat: continue
                    usd=to_usd(item.get("raw_price"),item.get("raw_currency"))
                    # No inventar conversión si el precio está en guaraníes u otra moneda.
                    if usd is None or usd <= 0:
                        continue
                    sale_usd=round(usd*(1+markup/100),2)
                    item_out={
                        "id":product_id(provider["name"],item.get("source_url",""),name),
                        "name":name,"brand":item.get("brand",""),"description":item.get("description",""),
                        "category":cat,"provider":provider["name"],"source_url":item.get("source_url",""),
                        "image_url":item.get("image_url",""),"source_price":usd,"source_currency":"USD",
                        "price_usd":sale_usd,"price_ars":round(sale_usd*ars_per_usd) if ars_per_usd else 0,
                        "stock_available":None,"featured":False,"updated_at":datetime.now(timezone.utc).isoformat(),
                        "source_price_currency":item.get("raw_currency","USD")
                    }
                    results[item_out["id"]]=item_out
            except Exception as exc:
                failures.append({"provider":provider["name"],"url":page_url,"error":str(exc)[:300]})
    output={"updated_at":datetime.now(timezone.utc).isoformat(),"ars_per_usd":ars_per_usd,
            "markup_percent":markup,"products":list(results.values()),"failures":failures,
            "note":"Si products está vacío, hay que validar acceso y adaptar el importador de cada proveedor."}
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Productos guardados: {len(results)}")
    print(f"Fuentes con error o sin productos detectados: {len(failures)}")
    for failure in failures: print(f"- {failure['provider']}: {failure['error']} ({failure['url']})")

if __name__=="__main__": main()
