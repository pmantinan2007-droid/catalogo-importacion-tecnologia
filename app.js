// Cambiá este valor por tu WhatsApp internacional sin +, espacios ni guiones.
const WHATSAPP_NUMBER = "5491100000000";
const DATA_URL = "data/products.json";
const FALLBACK_PRODUCTS = [
  {id:"demo-ps5",name:"Consola PlayStation 5 Slim Digital",brand:"Sony",category:"Gaming",provider:"Producto de ejemplo",price_usd:449,price_ars:0,image_url:"",description:"Consola de videojuegos. Ejemplo visual; reemplazar con datos importados.",source_url:"https://www.nissei.com/py/home",featured:true,demo:true},
  {id:"demo-watch",name:"Smartwatch deportivo Bluetooth",brand:"Smartwatch",category:"Smartwatches",provider:"Producto de ejemplo",price_usd:79,price_ars:0,image_url:"",description:"Reloj inteligente. Ejemplo visual; reemplazar con datos importados.",source_url:"https://www.cellshop.com.py/",featured:true,demo:true},
  {id:"demo-phone",name:"Smartphone Android 128 GB",brand:"Android",category:"Celulares",provider:"Producto de ejemplo",price_usd:219,price_ars:0,image_url:"",description:"Smartphone liberado. Ejemplo visual; reemplazar con datos importados.",source_url:"https://madridcenterimportados.com/es/home",featured:true,demo:true},
  {id:"demo-audio",name:"Auriculares inalámbricos Bluetooth",brand:"Audio",category:"Audio",provider:"Producto de ejemplo",price_usd:45,price_ars:0,image_url:"",description:"Auriculares compactos. Ejemplo visual; reemplazar con datos importados.",source_url:"https://www.shoppingchina.com.py/",featured:false,demo:true}
];
let products = [];
let activeCategory = "Todos";
const $ = (s) => document.querySelector(s);
const usd = (v) => new Intl.NumberFormat("en-US",{style:"currency",currency:"USD",maximumFractionDigits:2}).format(Number(v)||0);
const ars = (v) => new Intl.NumberFormat("es-AR",{style:"currency",currency:"ARS",maximumFractionDigits:0}).format(Number(v)||0);
function waLink(message){return `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(message)}`;}
function categoryOf(p){
  const s = `${p.category||""} ${p.name||""} ${p.brand||""} ${p.description||""}`.toLowerCase();
  if(/playstation|xbox|nintendo|consola|gaming|gamer|videojuego|joystick|gamepad/.test(s)) return "Gaming";
  if(/smartwatch|smart watch|apple watch|galaxy watch|reloj inteligente|wearable/.test(s)) return "Smartwatches";
  if(/iphone|smartphone|celular|telefono móvil|teléfono móvil|galaxy s\d|redmi note|moto g\d/.test(s)) return "Celulares";
  if(/auricular|headphone|headset|parlante|speaker|jbl|soundbar|audio/.test(s)) return "Audio";
  if(/cable|cargador|adaptador|funda|case|power bank|memoria|pendrive|usb|accesorio/.test(s)) return "Accesorios";
  return p.category || "Electrónica";
}
function cleanProduct(p){return {...p,category:categoryOf(p),price_usd:Number(p.price_usd)||0,price_ars:Number(p.price_ars)||0};}
function card(p){
  const image = p.image_url ? `<img src="${escapeHtml(p.image_url)}" alt="${escapeHtml(p.name)}" loading="lazy" onerror="this.remove();this.parentElement.querySelector('.product-placeholder').hidden=false">` : "";
  const placeholder = p.image_url ? "hidden" : "";
  const badge = p.featured ? `<span class="product-badge">Destacado</span>` : "";
  const demoLabel = p.demo ? "EJEMPLO — NO ES PRECIO VIGENTE" : (p.stock_available===false ? "Consultar disponibilidad" : "A pedido");
  const description = (p.description||"Consultá disponibilidad y características.").slice(0,115);
  const message = `Hola, quiero consultar por: ${p.name}. Precio de referencia: ${usd(p.price_usd)}${p.price_ars ? " / "+ars(p.price_ars):""}. Proveedor: ${p.provider||"a confirmar"}. ¿Me confirmás disponibilidad y precio final?`;
  return `<article class="product-card">
    <div class="product-image">${badge}${image}<div class="product-placeholder" ${placeholder}>⌁</div></div>
    <div class="product-info"><div class="product-provider">${escapeHtml(p.provider||"Catálogo")}</div>
    <h3 class="product-title">${escapeHtml(p.name||"Producto sin nombre")}</h3>
    <p class="product-desc">${escapeHtml(description)}</p>
    <div class="price-row"><div><div class="price-usd">${usd(p.price_usd)}</div><div class="price-ars">${p.price_ars>0?ars(p.price_ars):"ARS a confirmar"} · ${escapeHtml(demoLabel)}</div></div>
    <button class="order-btn" data-message="${escapeHtml(message)}">Consultar ↗</button></div>
    ${p.source_url?`<a class="source-link" href="${escapeHtml(p.source_url)}" target="_blank" rel="noopener noreferrer">Ver referencia de origen ↗</a>`:""}</div></article>`;
}
function escapeHtml(v){return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
function render(){
  const q=$("#searchInput").value.trim().toLowerCase();
  const provider=$("#providerFilter").value;
  const sort=$("#sortFilter").value;
  let filtered=products.filter(p=>{
    const hay=`${p.name} ${p.brand||""} ${p.category} ${p.description||""} ${p.provider||""}`.toLowerCase();
    return (!q||hay.includes(q))&&(activeCategory==="Todos"||p.category===activeCategory)&&(!provider||p.provider===provider);
  });
  if(sort==="price-asc") filtered.sort((a,b)=>a.price_usd-b.price_usd);
  if(sort==="price-desc") filtered.sort((a,b)=>b.price_usd-a.price_usd);
  if(sort==="name") filtered.sort((a,b)=>a.name.localeCompare(b.name));
  if(sort==="featured") filtered.sort((a,b)=>Number(Boolean(b.featured))-Number(Boolean(a.featured)));
  $("#productCount").textContent=`${filtered.length} producto${filtered.length===1?"":"s"}`;
  $("#productGrid").innerHTML=filtered.length?filtered.map(card).join(""):"";
  $("#emptyState").hidden=Boolean(filtered.length);
  $("#catalogFooterText").textContent=products.some(p=>p.demo)?"Versión inicial: los artículos de ejemplo no son ofertas reales.":"Precios sujetos a confirmación con el proveedor.";
  document.querySelectorAll(".order-btn").forEach(btn=>btn.addEventListener("click",()=>window.open(waLink(btn.dataset.message),"_blank","noopener")));
}
function setCategory(category){
  activeCategory=category;
  document.querySelectorAll(".category-tile").forEach(btn=>btn.classList.toggle("active",btn.dataset.category===category));
  render();
}
async function init(){
  $("#year").textContent=new Date().getFullYear();
  $("#headerWhatsApp").href=waLink("Hola, quiero consultar por el catálogo de tecnología.");
  $("#contactWhatsApp").href=waLink("Hola, quiero consultar por un producto de tecnología que no encuentro en el catálogo.");
  try{
    const response=await fetch(DATA_URL,{cache:"no-store"});
    if(!response.ok) throw new Error("No hay archivo de catálogo publicado");
    const data=await response.json();
    products=(Array.isArray(data.products)?data.products:[]).map(cleanProduct);
    if(!products.length) products=FALLBACK_PRODUCTS.map(cleanProduct);
  }catch(e){products=FALLBACK_PRODUCTS.map(cleanProduct);}
  const providers=[...new Set(products.map(p=>p.provider).filter(Boolean))].sort();
  $("#providerFilter").innerHTML='<option value="">Todos los proveedores</option>'+providers.map(p=>`<option value="${escapeHtml(p)}">${escapeHtml(p)}</option>`).join("");
  document.querySelectorAll(".category-tile").forEach(btn=>btn.addEventListener("click",()=>{setCategory(btn.dataset.category);$("#catalogo").scrollIntoView({behavior:"smooth",block:"start"});}));
  $("#searchInput").addEventListener("input",render);
  $("#providerFilter").addEventListener("change",render);
  $("#sortFilter").addEventListener("change",render);
  $("#clearFilters").addEventListener("click",()=>{$("#searchInput").value="";$("#providerFilter").value="";$("#sortFilter").value="featured";setCategory("Todos");});
  document.addEventListener("keydown",e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==="k"){e.preventDefault();$("#searchInput").focus();}});
  render();
}
init();
