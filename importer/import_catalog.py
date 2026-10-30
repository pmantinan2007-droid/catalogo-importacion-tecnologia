#!/usr/bin/env python3
"""Importador NEXO TECH: extrae productos reales publicados por los proveedores.
No inventa artículos ni precios. Si un sitio bloquea la consulta, lo deja informado.
"""
import os,re,json,time,hashlib,html
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
from pathlib import Path
from urllib.parse import urljoin,urlparse,urldefrag,parse_qs,urlencode,urlunparse
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'data/products.json'; REPORT=ROOT/'data/import_report.json'
MARGIN=Decimal(os.getenv('MARGIN_PERCENT','40')); MAX_PAGES=int(os.getenv('MAX_PAGES_PER_PROVIDER','18')); MAX_PRODUCTS=max(1,int(os.getenv('MAX_PRODUCTS','200'))); TIMEOUT=22; DELAY=float(os.getenv('REQUEST_DELAY_SECONDS','0.7'))
HEADERS={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36','Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8','Accept-Language':'es-PY,es;q=0.9,pt-BR;q=0.8,en;q=0.7','Cache-Control':'no-cache'}
S=requests.Session();S.headers.update(HEADERS); WARNINGS=[]; FETCH_STATS={}; FX={'PYG':None,'BRL':None,'ARS':None,'ars_source':None}
PROVIDERS=[
 {'name':'Cellshop','domain':'cellshop.com.py','starts':['https://cellshop.com.py/todos-los-departamentos/tecnologia/apple/iphone','https://cellshop.com.py/todos-los-departamentos/tecnologia/apple/iphone?p=2','https://cellshop.com.py/todos-los-departamentos/tecnologia/apple','https://cellshop.com.py/5684267-adaptador-wireless-carplay-joog-ai-box-b11']},
 {'name':'Nissei','domain':'nissei.com','starts':['https://nissei.com/py/electronica/celulares-accesorios-telecomunicaciones/celulares-accesorios/xiaomi-redmi-note-17-4g-dual-128-gb-4-gb-ram-negro','https://nissei.com/py/electronica/realme-p4-power-rmx5107-5g-dual-512-gb-silver','https://nissei.com/py/electronica/celulares-accesorios-telecomunicaciones/xiaomi-17t-5g-dual-512-gb-blue','https://nissei.com/py/electronica/']},
 {'name':'Madrid Center','domain':'madridcenterimportados.com','starts':['https://madridcenterimportados.com/','https://madridcenterimportados.com/es/home','https://madridcenterimportados.com/es/celulares-y-smartphones','https://madridcenterimportados.com/es/informatica']},
 {'name':'Shopping China','domain':'shoppingchina.com.py','starts':['https://www.shoppingchina.com.py/electronicos/video-games','https://www.shoppingchina.com.py/electronicos.celulares?page=1','https://www.shoppingchina.com.py/electronicos.auriculares?page=1','https://www.shoppingchina.com.py/informatica.notebooks?page=1','https://www.shoppingchina.com.py/site/search?query=smartphone','https://www.shoppingchina.com.py/site/search?query=notebook','https://www.shoppingchina.com.py/site/search?query=consola','https://www.shoppingchina.com.py/site/search?query=auricular','https://www.shoppingchina.com.py/site/search?query=smartwatch']},
]
INCLUDE=re.compile(r'iphone|smartphone|celular|phone|galaxy|xiaomi|motorola|playstation|ps5|ps4|xbox|nintendo|consola|gaming|gamer|gamepad|joystick|smart.?watch|apple watch|galaxy watch|auricular|aud[ií]fono|headphone|headset|parlante|speaker|soundbar|jbl|audio|cable|cargador|adaptador|power.?bank|tablet|ipad|notebook|laptop|macbook|ssd|memoria ram|placa de video|teclado|mouse|webcam|dji|drone|airpods|monitor|router|wi.?fi|bluetooth|smart.?tv|televisor|proyector|impresora|streaming|disco s[oó]lido|procesador|placa madre|gpu|inform[aá]tica|computadora',re.I)
EXCLUDE=re.compile(r'perfume|colonia|bebida|alimento|suplemento|cigarrillo|tabaco|ropa|calzado|maquillaje|mueble|juguete infantil',re.I)
TECH_LINK=re.compile(r'celular|smartphone|consol|playstation|xbox|nintendo|audio|auricular|electron|inform[aá]tica|gamer|gaming|smart.?watch|reloj|tablet|notebook|comput|tv|televisor|accesorio|c[aá]mara|drone|iphone|category|categoria|catalogo|products|product|search',re.I)

def clean(x): return re.sub(r'\s+',' ',BeautifulSoup(str(x or ''),'html.parser').get_text(' ',strip=True)).strip()
def absurl(u,base):
 if not u:return ''
 u=html.unescape(str(u).strip())
 if u.startswith(('data:','javascript:','mailto:','#')):return ''
 return urldefrag(urljoin(base,u))[0]
def number(raw):
 if raw is None:return None
 x=re.sub(r'[^\d,.\-]','',str(raw))
 if not x:return None
 if ',' in x and '.' in x:x=x.replace('.','').replace(',','.') if x.rfind(',')>x.rfind('.') else x.replace(',','')
 elif ',' in x:x=x.replace(',','.') if len(x.rsplit(',',1)[-1]) in (1,2) else x.replace(',','')
 elif x.count('.')>1:x=x.replace('.','')
 elif '.' in x and len(x.rsplit('.',1)[-1])==3:x=x.replace('.','')
 try:
  v=Decimal(x);return v if v>0 else None
 except InvalidOperation:return None

def fetch(url,provider='desconocido'):
 try:
  r=S.get(url,timeout=TIMEOUT); FETCH_STATS.setdefault(provider,{'ok':0,'blocked':0,'errors':[]})
  if r.status_code in (401,403,429):
   FETCH_STATS[provider]['blocked']+=1;FETCH_STATS[provider]['errors'].append(f'HTTP {r.status_code}: {url}')
   WARNINGS.append({'provider':provider,'url':url,'error':f'HTTP {r.status_code} (bloqueo/limitación del proveedor)' });return None,url
  r.raise_for_status()
  if not r.encoding or r.encoding.lower()=='iso-8859-1':r.encoding=r.apparent_encoding
  FETCH_STATS[provider]['ok']+=1;time.sleep(DELAY);return r.text,r.url
 except Exception as e:
  FETCH_STATS.setdefault(provider,{'ok':0,'blocked':0,'errors':[]})['errors'].append(f'{type(e).__name__}: {str(e)[:150]}')
  WARNINGS.append({'provider':provider,'url':url,'error':f'{type(e).__name__}: {str(e)[:180]}' });return None,url

def exchange_rates():
 # Tasas oficiales de referencia para convertir PYG/BRL a USD y USD a ARS.
 try:
  d=S.get('https://open.er-api.com/v6/latest/USD',timeout=15).json();rates=d.get('rates',{})
  for c in ('PYG','BRL'):
   if rates.get(c):FX[c]=Decimal(str(rates[c]))
  if rates.get('ARS'):
   FX['ARS']=Decimal(str(rates['ARS']));FX['ars_source']='API de cambio USD/ARS (respaldo; no es dólar blue)'
 except Exception as e:WARNINGS.append({'source':'tipo de cambio API','error':str(e)[:160]})
 # Prioridad al dólar blue vendedor de DolarHoy. El HTML puede variar, por eso se prueban varios patrones.
 try:
  r=S.get('https://dolarhoy.com/',timeout=15); r.raise_for_status(); soup=BeautifulSoup(r.text,'html.parser')
  text=clean(soup.get_text(' ',strip=True))
  patterns=[r'd[oó]lar\s+blue.{0,220}?venta\s*:?\s*\$?\s*([\d.]+(?:,\d{1,2})?)',r'blue.{0,140}?\$\s*([\d.]+(?:,\d{1,2})?)',r'd[oó]lar\s+blue.{0,100}?([1-9][\d.]{2,})']
  for pat in patterns:
   m=re.search(pat,text,re.I)
   if m:
    n=number(m.group(1))
    if n and n>500:FX['ARS']=n;FX['ars_source']='DolarHoy - dólar blue venta';break
 except Exception as e:WARNINGS.append({'source':'DolarHoy','error':str(e)[:160]})
 if not FX['ARS']:
  fallback=number(os.getenv('ARS_PER_USD'))
  if fallback and fallback>500:FX['ARS']=fallback;FX['ars_source']='ARS_PER_USD configurado en GitHub (respaldo)'
 if not FX['ARS']:
  WARNINGS.append({'source':'tipo de cambio','error':'No se obtuvo dólar blue de DolarHoy ni variable ARS_PER_USD; los precios ARS quedan sin actualizar.'})

def currency(text,explicit=''):
 c=str(explicit or '').upper().strip()
 if c in ('PYG','USD','BRL','ARS'):return c
 t=str(text or '')
 if '₲' in t or re.search(r'\bGs\.?|\bPYG\b|guaran[ií]',t,re.I):return 'PYG'
 if 'R$' in t or re.search(r'\bBRL\b',t,re.I):return 'BRL'
 if re.search(r'US\$|\bUSD\b',t,re.I):return 'USD'
 if re.search(r'\bARS\b|pesos argentinos',t,re.I):return 'ARS'
 return ''
def price_in_text(text):
 for pat,cur in [(r'(?:Gs\.?|PYG|₲)\s*([\d.,]+)','PYG'),(r'([\d.,]+)\s*(?:Gs\.?|PYG|₲)','PYG'),(r'(?:US\$|USD)\s*([\d.,]+)','USD'),(r'(?<![A-Z])\$\s*([\d.,]+)','USD'),(r'AR\$\s*([\d.,]+)','ARS'),(r'R\$\s*([\d.,]+)','BRL'),(r'([\d.,]+)\s*USD\b','USD'),(r'ARS\s*\$?\s*([\d.,]+)','ARS')]:
  m=re.search(pat,str(text or ''),re.I)
  if m:
   n=number(m.group(1))
   if n:return n,cur
 return None,''
def usd_value(amount,cur):
 if not amount:return None
 if cur=='USD':return amount
 if cur=='PYG' and FX['PYG']:return amount/FX['PYG']
 if cur=='BRL' and FX['BRL']:return amount/FX['BRL']
 if cur=='ARS' and FX['ARS']:return amount/FX['ARS']
 return None

def category(name,desc=''):
 s=(name+' '+desc).lower()
 for pattern,label in [(r'playstation|ps5|ps4|xbox|nintendo|consola|gaming|gamer|gamepad|joystick','Gaming'),(r'smart.?watch|apple watch|galaxy watch|reloj inteligente','Smartwatches'),(r'iphone|smartphone|celular|galaxy s\d|redmi note|moto g\d','Celulares'),(r'auricular|aud[ií]fono|headphone|headset|parlante|speaker|soundbar|audio|jbl|airpods','Audio'),(r'tablet|ipad','Tablets'),(r'notebook|laptop|macbook|ssd|memoria ram|placa de video|teclado|mouse|monitor|webcam|router|procesador|placa madre|computadora','Informática'),(r'televisor|smart.?tv|proyector|streaming','TV y video'),(r'cable|cargador|adaptador|funda|power.?bank|memoria|pendrive|usb|accesorio','Accesorios'),(r'c[aá]mara|drone|dron','Cámaras')]:
  if re.search(pattern,s):return label
 return 'Electrónica portátil'
def in_stock(obj,text):
 av=str(obj or '').lower();t=str(text or '').lower()
 if any(x in av for x in ('outofstock','soldout','discontinued')):return False
 if any(x in t for x in ('sin stock','agotado','fuera de stock','out of stock','esgotado')):return False
 if any(x in av for x in ('instock','limitedavailability','preorder')):return True
 if re.search(r'en stock|disponible|in stock',t):return True
 return None
def product_record(name,url,provider,price,cur,image='',brand='',desc='',sku='',stock=None):
 name=clean(name)
 if not name or not INCLUDE.search(name) or EXCLUDE.search(name):return None
 usd=usd_value(price,cur)
 if not usd or usd<=0:return None
 sale=(usd*(Decimal('1')+MARGIN/Decimal('100'))).quantize(Decimal('0.01'));ars=round(sale*FX['ARS']) if FX['ARS'] else 0
 key=hashlib.sha1((provider+'|'+url).encode()).hexdigest()[:16]
 return {'id':key,'name':name,'brand':clean(brand),'description':clean(desc)[:500],'category':category(name,desc),'provider':provider,'source_url':url,'image_url':image,'source_price':float(price),'source_currency':cur,'price_usd':float(sale),'price_ars':ars,'stock_available':stock,'featured':False,'updated_at':datetime.now(timezone.utc).isoformat()}

def walk_json(data):
 if isinstance(data,list):
  for x in data:yield from walk_json(x)
 elif isinstance(data,dict):
  yield data
  for v in data.values():
   if isinstance(v,(dict,list)):yield from walk_json(v)
def extract_product_image(soup, base_url):
 # Preferencia: imagen de producto declarada por OpenGraph/Twitter, JSON-LD y galería principal.
 for sel,attr in [('meta[property="og:image"]','content'),('meta[property="og:image:secure_url"]','content'),('meta[name="twitter:image"]','content'),('[itemprop="image"]','content'),('[itemprop="image"]','src')]:
  el=soup.select_one(sel)
  if el and el.get(attr):
   u=absurl(el.get(attr),base_url)
   if u and not u.startswith('data:'):return u
 for sc in soup.select('script[type="application/ld+json"]'):
  try: data=json.loads(sc.string or sc.get_text())
  except Exception: continue
  for obj in walk_json(data):
   typ=obj.get('@type',[]);typ=[typ] if isinstance(typ,str) else typ
   if any(str(x).lower()=='product' for x in typ):
    im=obj.get('image') or []
    if isinstance(im,str):im=[im]
    if isinstance(im,dict):im=[im.get('url') or im.get('contentUrl')]
    for raw in im:
     if isinstance(raw,dict):raw=raw.get('url') or raw.get('contentUrl')
     u=absurl(raw,base_url)
     if u:return u
 selectors=['.fotorama__stage img','.product-image-photo','.gallery-placeholder img','.product-image img','[data-gallery-role="gallery"] img','main img']
 for sel in selectors:
  for el in soup.select(sel):
   raw=el.get('data-zoom-image') or el.get('data-src') or el.get('data-lazy-src') or el.get('data-original') or el.get('src')
   if not raw and el.get('srcset'):raw=el.get('srcset').split(',')[-1].strip().split(' ')[0]
   u=absurl(raw,base_url)
   if u and not re.search(r'logo|icon|banner|pixel|placeholder',u,re.I):return u
 return ''

def enrich_existing_product(item):
 # Relee cada ficha guardada para completar foto y actualizar precio solo con precio vigente detectado.
 url=item.get('source_url','')
 if not url:return item
 raw,final=fetch(url,'Imagenes y actualización de fichas')
 if not raw:return item
 soup=BeautifulSoup(raw,'html.parser')
 if not item.get('image_url'):
  item['image_url']=extract_product_image(soup,final)
 # Preferir precio del JSON-LD de la ficha; si no existe, buscar texto cercano al precio.
 for sc in soup.select('script[type="application/ld+json"]'):
  try:data=json.loads(sc.string or sc.get_text())
  except Exception:continue
  for obj in walk_json(data):
   typ=obj.get('@type',[]);typ=[typ] if isinstance(typ,str) else typ
   if not any(str(x).lower()=='product' for x in typ):continue
   offer=obj.get('offers') or {};offer=offer[0] if isinstance(offer,list) and offer else offer
   if isinstance(offer,dict):
    amt=number(offer.get('price') or offer.get('lowPrice'));cur=currency('',offer.get('priceCurrency',''))
    if amt and cur:
     usd=usd_value(amt,cur)
     if usd:
      sale=(usd*(Decimal('1')+MARGIN/Decimal('100'))).quantize(Decimal('0.01'))
      item.update({'source_price':float(amt),'source_currency':cur,'price_usd':float(sale),'price_ars':round(sale*FX['ARS']) if FX['ARS'] else 0,'price_is_snapshot':False,'price_checked_at':datetime.now(timezone.utc).isoformat()})
   av=offer.get('availability','') if isinstance(offer,dict) else ''
   st=in_stock(av,clean(soup.get_text(' ',strip=True)))
   if st is not None:item['stock_available']=st
   break
 item['image_checked_at']=datetime.now(timezone.utc).isoformat()
 return item

def jsonld(soup,url,provider):
 out=[]
 for sc in soup.select('script[type="application/ld+json"]'):
  try:data=json.loads(sc.string or sc.get_text())
  except Exception:continue
  for o in walk_json(data):
   typ=o.get('@type',[]);typ=[typ] if isinstance(typ,str) else typ
   if not any(str(x).lower()=='product' for x in typ):continue
   offer=o.get('offers') or {};offer=offer[0] if isinstance(offer,list) and offer else offer
   if not isinstance(offer,dict):offer={}
   raw=number(offer.get('price') or offer.get('lowPrice'));cur=currency(json.dumps(offer,ensure_ascii=False),offer.get('priceCurrency',''))
   if not raw:raw,cur=price_in_text(clean(soup.get_text(' ',strip=True)))
   if not cur:cur=currency(clean(soup.get_text(' ',strip=True)))
   img=o.get('image') or '';img=img[0] if isinstance(img,list) and img else img
   if isinstance(img,dict):img=img.get('url') or img.get('contentUrl') or ''
   brand=o.get('brand') or '';brand=brand.get('name','') if isinstance(brand,dict) else brand
   rec=product_record(o.get('name'),absurl(o.get('url') or url,url),provider,raw,cur,absurl(img,url),brand,o.get('description',''),o.get('sku') or o.get('mpn',''),in_stock(offer.get('availability'),clean(soup.get_text(' ',strip=True))))
   if rec:out.append(rec)
 return out

def cards(soup,url,provider):
 """Try known card classes and then product-like links with nearby ancestor data."""
 out=[];seen=set()
 selectors=['.product-item','.product-card','.product-miniature','.product-layout','li.product','[data-product-id]','article.product','[class*="product-card"]','[class*="product-item"]','[class*="product-box"]','[class*="product"]']
 nodes=[]
 for sel in selectors:
  try:nodes.extend(soup.select(sel))
  except Exception:pass
 # Broad fallback: walk each link and choose the closest ancestor that contains a recognizable price.
 for a in soup.select('a[href]'):
  link=absurl(a.get('href'),url)
  if not link:continue
  host=urlparse(link).netloc.lower().replace('www.','');domain=provider_domain(provider)
  if domain not in host:continue
  path=urlparse(link).path.lower()
  if not path or path in ('/','/py/home','/es/home','/site/index') or re.search(r'login|customer|checkout|wishlist|compare|cart|politica|contacto',path):continue
  parent=a
  for _ in range(5):
   if parent.parent is None:break
   parent=parent.parent
   txt=clean(parent.get_text(' ',strip=True))
   if len(txt)>500:continue
   if price_in_text(txt)[0] and parent.select_one('img'):
    nodes.append(parent);break
 for card in nodes:
  a=card.select_one('a[href]')
  if not a:continue
  link=absurl(a.get('href'),url);host=urlparse(link).netloc.lower().replace('www.','')
  if provider_domain(provider) not in host or link in seen:continue
  txt=clean(card.get_text(' ',strip=True))
  title=card.select_one('[itemprop="name"],.product-item-link,.product-title,.product-name,.name,h2,h3,h4,[class*="product-name"],[class*="product-title"]')
  img=card.select_one('img')
  name=clean((title.get('content') if title and title.has_attr('content') else title.get_text(' ',strip=True) if title else '') or a.get('title') or (img.get('alt') if img else '') or a.get_text(' ',strip=True))
  # Reject category tiles and non-product links.
  val,cur=price_in_text(txt)
  if not val:
   el=card.select_one('[data-price-amount],.price,[class*="price"]')
   if el:val,cur=price_in_text(el.get_text(' ',strip=True))
   if not val and el and el.get('data-price-amount'):val=number(el.get('data-price-amount'));cur=currency(txt)
  if not val:continue
  image_raw=''
  if img:
   image_raw=img.get('data-src') or img.get('data-lazy-src') or img.get('data-original') or img.get('data-original-src') or img.get('src') or ''
   if not image_raw and img.get('srcset'):
    image_raw=img.get('srcset').split(',')[0].strip().split(' ')[0]
  if not image_raw:
   pic=card.select_one('picture source[srcset]')
   if pic:image_raw=pic.get('srcset','').split(',')[0].strip().split(' ')[0]
  image=absurl(image_raw,url)
  if not image:image=extract_product_image(soup,link)
  rec=product_record(name,link,provider,val,cur,image,desc=txt,stock=in_stock('',txt))
  if rec:out.append(rec);seen.add(link)
 return out

def provider_domain(name):return {'Cellshop':'cellshop.com.py','Nissei':'nissei.com','Madrid Center':'madridcenterimportados.com','Shopping China':'shoppingchina.com.py'}.get(name,'')
def links_to_follow(soup,url,domain):
 out=[]
 for a in soup.select('a[href]'):
  link=absurl(a.get('href'),url)
  if not link:continue
  host=urlparse(link).netloc.lower().replace('www.','')
  if domain not in host:continue
  txt=(a.get_text(' ',strip=True)+' '+str(a.get('title') or '')+' '+urlparse(link).path).strip()
  if TECH_LINK.search(txt) and not re.search(r'login|customer|checkout|wishlist|compare|cart|politica|contacto|sobre-nos|about-us',link,re.I):out.append(link)
 # Follow next pages for Nissei Magento and Shopping China search pages.
 parsed=urlparse(url);qs=parse_qs(parsed.query)
 if 'nissei.com' in domain and 'p' in qs:
  n=int(qs.get('p',['1'])[0]);
  if n<10:out.append(urlunparse(parsed._replace(query=urlencode({**{k:v[0] for k,v in qs.items()},'p':n+1}))))
 if 'shoppingchina.com.py' in domain and '/site/search' in parsed.path:
  n=int(qs.get('page',['1'])[0]);
  if n<8:out.append(urlunparse(parsed._replace(query=urlencode({**{k:v[0] for k,v in qs.items()},'page':n+1}))))
 return list(dict.fromkeys(out))

def scrape_provider(p):
 found={};queue=list(p['starts']);visited=set()
 while queue and len(visited)<MAX_PAGES and len(found)<800:
  url=queue.pop(0)
  if url in visited:continue
  visited.add(url);raw,final=fetch(url,p['name'])
  if not raw:continue
  soup=BeautifulSoup(raw,'html.parser');candidates=jsonld(soup,final,p['name']);candidates+=cards(soup,final,p['name'])
  for item in candidates:found[item['source_url']]=item
  for link in links_to_follow(soup,final,p['domain']):
   if link not in visited and link not in queue and len(queue)<MAX_PAGES*3:queue.append(link)
  print(f"[{p['name']}] página {len(visited)}/{MAX_PAGES}; productos válidos {len(found)}")
 return list(found.values()),len(visited)

def main():
 exchange_rates();all_products=[];report=[]
 for p in PROVIDERS:
  if len({x.get('source_url') for x in all_products if x.get('source_url')}) >= MAX_PRODUCTS:
   report.append({'provider':p['name'],'pages_checked':0,'products_found':0,'status':'límite global alcanzado','details':[]})
   continue
  try:
   products,pages=scrape_provider(p);all_products.extend(products)
   stat=FETCH_STATS.get(p['name'],{});blocked=stat.get('blocked',0);ok=stat.get('ok',0)
   status='ok' if products else ('bloqueado por proveedor' if blocked and not ok else 'sin productos extraídos')
   report.append({'provider':p['name'],'pages_checked':pages,'pages_loaded':ok,'pages_blocked':blocked,'products_found':len(products),'status':status,'details':(stat.get('errors') or [])[:8]})
  except Exception as e:
   WARNINGS.append({'provider':p['name'],'error':f'{type(e).__name__}: {str(e)[:250]}'})
   report.append({'provider':p['name'],'pages_checked':0,'products_found':0,'status':'error'})
 unique={x['source_url']:x for x in all_products if x.get('source_url') and x.get('price_usd')}
 # Límite estricto: nunca publicar más de MAX_PRODUCTS productos.
 unique=dict(list(unique.items())[:MAX_PRODUCTS])
 OUT.parent.mkdir(parents=True,exist_ok=True)
 # Fusionar: si un proveedor bloquea el scraping, no se borra el catálogo que ya se ve.
 previous={}
 if OUT.exists():
  try:
   old_data=json.loads(OUT.read_text(encoding='utf-8'))
   for item in old_data.get('products',[]):
    k=(item.get('provider','')+'|'+item.get('name','')).lower()
    if k: previous[k]=item
  except Exception: pass
 for item in unique.values():
  k=(item.get('provider','')+'|'+item.get('name','')).lower()
  previous[k]=item
 # Recalcular ARS con la cotización de esta ejecución y completar imágenes faltantes desde la ficha original.
 for item in list(previous.values()):
  cur=item.get('source_currency');amount=number(item.get('source_price'))
  usd=usd_value(amount,cur) if amount and cur else None
  if usd:
   sale=(usd*(Decimal('1')+MARGIN/Decimal('100'))).quantize(Decimal('0.01'))
   item['price_usd']=float(sale)
   item['price_ars']=round(sale*FX['ARS']) if FX['ARS'] else 0
  if not item.get('image_url') or item.get('price_is_snapshot'):
   try:enrich_existing_product(item)
   except Exception as e:WARNINGS.append({'provider':item.get('provider'),'url':item.get('source_url'),'error':'No se pudo completar ficha: '+str(e)[:120]})
 merged=list(previous.values())[:MAX_PRODUCTS]
 if merged or not OUT.exists():
  data={'updated_at':datetime.now(timezone.utc).isoformat(),'ars_per_usd':float(FX['ARS']) if FX['ARS'] else None,'ars_source':FX['ars_source'],'pyg_per_usd':float(FX['PYG']) if FX['PYG'] else None,'brl_per_usd':float(FX['BRL']) if FX['BRL'] else None,'markup_percent':float(MARGIN),'max_products':MAX_PRODUCTS,'products':merged,'failures':WARNINGS,'note':'Catálogo combinado: los productos capturados se actualizan; los de referencia previos se conservan si un proveedor bloquea la extracción. Confirmar precio y stock antes de vender.'}
  OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
 else:WARNINGS.append({'warning':'Sin resultados nuevos: se conservó el catálogo anterior.'})
 REPORT.write_text(json.dumps({'updated_at':datetime.now(timezone.utc).isoformat(),'exchange_rates':{'ARS':str(FX['ARS']) if FX['ARS'] else None,'ARS_source':FX['ars_source'],'PYG_per_USD':str(FX['PYG']) if FX['PYG'] else None,'BRL_per_USD':str(FX['BRL']) if FX['BRL'] else None},'total_products_extracted':len(unique),'total_products_in_catalog':len(merged),'max_products':MAX_PRODUCTS,'products_with_images':sum(1 for x in merged if x.get('image_url')),'products_without_images':sum(1 for x in merged if not x.get('image_url')),'providers':report,'warnings':WARNINGS},ensure_ascii=False,indent=2),encoding='utf-8')
 print('PRODUCTOS REALES EXTRAÍDOS:',len(unique))
 print('LÍMITE MÁXIMO DEL CATÁLOGO:',MAX_PRODUCTS)
 for r in report:print(f"- {r['provider']}: {r['products_found']} productos; {r.get('pages_loaded',0)} páginas leídas, {r.get('pages_blocked',0)} bloqueadas ({r['status']})")
 print('Informe escrito en data/import_report.json')
 if not FX['ARS']:print('AVISO: no se obtuvo cotización ARS; configurar la variable ARS_PER_USD en GitHub > Settings > Secrets and variables > Actions > Variables.')
if __name__=='__main__':main()
