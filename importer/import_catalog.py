#!/usr/bin/env python3
"""Best-effort importer for publicly accessible product pages. Never fabricates prices."""
import json, os, re, hashlib, html
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'importer/providers.json'; OUTPUT=ROOT/'data/products.json'
ALLOWED=re.compile(r'iphone|smartphone|celular|phone|galaxy|xiaomi|motorola|playstation|xbox|nintendo|console|consola|gaming|gamer|gamepad|joystick|smartwatch|smart watch|apple watch|galaxy watch|auricular|headphone|headset|parlante|speaker|jbl|audio|cable|cargador|adaptador|power bank|tablet|notebook|laptop|ssd|memoria ram|placa de video|teclado|mouse|webcam|dji|drone|airpods|macbook',re.I)
SKIP=re.compile(r'perfume|bebida|alimento|suplemento|cigarrillo|tabaco|ropa|calzado|maquillaje|mueble',re.I)
PRICE_RE=re.compile(r'(?:Gs\.?|₲|US\$|USD|R\$|R\s*\$|\$)\s*[\d.,]+|[\d.,]+\s*(?:Gs\.?|₲|USD)',re.I)
def clean(s): return re.sub(r'\s+',' ',BeautifulSoup(str(s or ''),'html.parser').get_text(' ',strip=True)).strip()
def price_number(s):
    s=re.sub(r'[^\d,.]','',str(s or ''))
    if not s:return None
    # Paraguay listings commonly use dots as thousands separators; decimal currencies use cents.
    if ',' in s and '.' in s:
        s=s.replace('.','').replace(',','.') if s.rfind(',')>s.rfind('.') else s.replace(',','')
    elif ',' in s:
        s=s.replace(',','.') if len(s.rsplit(',',1)[-1]) in (1,2) else s.replace(',','')
    elif '.' in s and len(s.rsplit('.',1)[-1])==3:s=s.replace('.','')
    try:return float(s)
    except:return None
def currency_for(text):
    t=(text or '').upper()
    if '₲' in t or 'GS' in t or 'GUARAN' in t:return 'PYG'
    if 'R$' in t:return 'BRL'
    if 'US$' in t or 'USD' in t:return 'USD'
    # A bare $ is ambiguous; never assume it is USD.
    return ''
def absurl(u,base):return urljoin(base,html.unescape(str(u or '').strip())) if u else ''
def product_objects(soup,url,provider):
    out=[]
    for sc in soup.select('script[type="application/ld+json"]'):
        try:d=json.loads(sc.string or sc.get_text())
        except:continue
        stack=d if isinstance(d,list) else [d]
        while stack:
            o=stack.pop()
            if isinstance(o,list):stack.extend(o);continue
            if not isinstance(o,dict):continue
            if '@graph' in o:stack.append(o['@graph'])
            typ=o.get('@type',[]);typ=[typ] if isinstance(typ,str) else typ
            if not any(str(x).lower()=='product' for x in typ):continue
            offer=o.get('offers') or {};offer=offer[0] if isinstance(offer,list) and offer else offer
            if not isinstance(offer,dict):offer={}
            name=clean(o.get('name'))
            if not name:continue
            img=o.get('image') or '';img=img[0] if isinstance(img,list) and img else img
            raw=offer.get('price') or offer.get('lowPrice');cur=offer.get('priceCurrency') or ''
            out.append(dict(name=name,brand=clean(o.get('brand',{}).get('name') if isinstance(o.get('brand'),dict) else o.get('brand')),description=clean(o.get('description')),image_url=absurl(img,url),source_url=absurl(o.get('url') or url,url),raw_price=price_number(raw),raw_currency=str(cur).upper(),provider=provider))
    return out

def card_candidates(soup,url,provider):
    out=[]; seen=set()
    # Common ecommerce product cards and product links; only include cards with explicit price text.
    selectors=['.product-item','.product-card','.product-miniature','.product-layout','li.product','[data-product-id]','article']
    cards=[]
    for sel in selectors: cards.extend(soup.select(sel))
    for card in cards:
        a=card.select_one('a[href]'); title=card.select_one('[itemprop="name"],.product-title,.product-name,.name,h2,h3,h4')
        img=card.select_one('img')
        name=clean((title.get('content') if title and title.has_attr('content') else title.get_text(' ',strip=True) if title else '') or (img.get('alt') if img else ''))
        if not name or not ALLOWED.search(name) or SKIP.search(name) or not a:continue
        href=absurl(a.get('href'),url)
        if not href or href in seen or urlparse(href).netloc not in ('',urlparse(url).netloc):continue
        txt=clean(card.get_text(' ',strip=True)); match=PRICE_RE.search(txt)
        if not match:continue
        cur=currency_for(match.group(0)); val=price_number(match.group(0))
        image=img.get('data-src') or img.get('data-lazy-src') or img.get('src') if img else ''
        if image and image.startswith('data:'): image=img.get('data-src') or img.get('data-lazy-src') or ''
        seen.add(href);out.append(dict(name=name,brand='',description=txt[:500],image_url=absurl(image,url),source_url=href,raw_price=val,raw_currency=cur,provider=provider))
    return out

def category(name,desc=''):
    s=(name+' '+desc).lower()
    if re.search(r'playstation|xbox|nintendo|consola|gaming|gamer|gamepad|joystick|videojuego',s):return 'Gaming'
    if re.search(r'smartwatch|smart watch|apple watch|galaxy watch|reloj inteligente',s):return 'Smartwatches'
    if re.search(r'iphone|smartphone|celular|galaxy s\d|redmi note|moto g\d',s):return 'Celulares'
    if re.search(r'auricular|headphone|headset|parlante|speaker|soundbar|audio|jbl|airpods',s):return 'Audio'
    if re.search(r'cable|cargador|adaptador|funda|power bank|memoria|pendrive|usb|accesorio',s):return 'Accesorios'
    if re.search(r'tablet|notebook|laptop|ssd|placa de video|memoria ram|teclado|mouse|webcam|monitor|dji|drone',s):return 'Electrónica portátil'
    return ''
def to_usd(price,currency):
    if price is None:return None
    c=(currency or '').upper().strip()
    if c in ('USD','US$'):return float(price)
    # PYG/BRL are intentionally not converted until a verified FX source is configured.
    return None

def main():
    cfg=json.loads(CONFIG.read_text(encoding='utf-8'));session=requests.Session();session.headers['User-Agent']=cfg.get('user_agent','Mozilla/5.0')
    timeout=int(cfg.get('timeout_seconds',25));markup=float(cfg.get('markup_percent',40));fx=price_number(os.getenv(cfg.get('ars_per_usd_env','ARS_PER_USD')))
    results={};failures=[]
    for p in cfg['providers']:
        if not p.get('enabled',True):continue
        for page in p.get('category_urls',[])[:int(cfg.get('max_category_pages_per_provider',4))]:
            try:
                r=session.get(page,timeout=timeout);r.raise_for_status();soup=BeautifulSoup(r.text,'html.parser')
                found=product_objects(soup,page,p['name'])
                if not found:found=card_candidates(soup,page,p['name'])
                if not found:failures.append({'provider':p['name'],'url':page,'error':'No se pudieron extraer productos públicos de esta página; requiere revisar estructura/feed/API.'})
                for x in found:
                    cat=category(x['name'],x.get('description',''))
                    if not cat or not ALLOWED.search(x['name']+' '+x.get('description','')) or SKIP.search(x['name']):continue
                    usd=to_usd(x.get('raw_price'),x.get('raw_currency'))
                    # Only display prices that are explicitly denominated in USD; don't guess exchange rates.
                    if not usd or usd<=0 or not x.get('image_url'):continue
                    sale=round(usd*(1+markup/100),2);key=hashlib.sha1((p['name']+'|'+x['source_url']).encode()).hexdigest()[:16]
                    results[key]={'id':key,'name':x['name'],'brand':x.get('brand',''),'description':x.get('description',''),'category':cat,'provider':p['name'],'source_url':x['source_url'],'image_url':x['image_url'],'source_price':usd,'source_currency':'USD','price_usd':sale,'price_ars':round(sale*fx) if fx else 0,'stock_available':None,'featured':False,'updated_at':datetime.now(timezone.utc).isoformat()}
            except Exception as e:failures.append({'provider':p['name'],'url':page,'error':str(e)[:250]})
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps({'updated_at':datetime.now(timezone.utc).isoformat(),'ars_per_usd':fx,'markup_percent':markup,'products':list(results.values()),'failures':failures,'note':'No se inventan productos ni precios. Guaraníes/reales se excluyen hasta configurar conversión verificable.'},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Productos reales importados:',len(results));print('Avisos de proveedores:',len(failures))
    for f in failures:print('-',f['provider'],f['error'])
if __name__=='__main__':main()
