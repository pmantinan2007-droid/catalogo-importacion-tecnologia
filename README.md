# Catálogo de importación de tecnología — NEXO TECH

Catálogo estático con diseño oscuro/azul, búsqueda, filtros, precios en USD/ARS y consultas por WhatsApp. El catálogo se alimenta desde `data/products.json`.

## Importación automática

El workflow de GitHub Actions consulta los sitios públicos de **Cellshop, Nissei, Madrid Center Importados y Shopping China** cada 6 horas (también se puede ejecutar manualmente desde **Actions → Actualizar catálogo → Run workflow**).

El importador intenta leer datos estructurados de producto (JSON-LD), metadatos y tarjetas de catálogo. Solo publica productos que tengan nombre, URL y precio verificable convertido a USD; no genera productos de demostración ni inventa precios. Aplica un margen del 40%.

- Conversión desde guaraníes/reales: intenta usar tasas de referencia públicas.
- Precio ARS: intenta leer dólar blue venta de DolarHoy. Si no se puede, usa la variable `ARS_PER_USD` configurada en GitHub → Settings → Secrets and variables → Actions → Variables.
- El detalle de páginas consultadas, productos por proveedor y errores se guarda en `data/import_report.json`.
- Si una ejecución no encuentra ningún producto, conserva el catálogo anterior para evitar vaciar la web accidentalmente.
- Los proveedores pueden cambiar sus páginas o bloquear consultas automatizadas. No se evaden CAPTCHAs, inicios de sesión ni controles de acceso. El primer resultado debe revisarse en Actions y en el informe.
- Las imágenes se muestran desde la URL pública de origen; revisá los términos de uso de cada proveedor.
- El stock se presenta como dato orientativo cuando la página lo permite. Antes de confirmar un pedido, hay que verificar disponibilidad y precio final con el proveedor.

## Instalar el paquete

1. Descargá y descomprimí el ZIP completo.
2. En GitHub, abrí el repositorio `catalogo-importacion-tecnologia`.
3. Reemplazá los archivos del repositorio por los de este paquete, manteniendo los nombres y carpetas. Si preferís hacerlo manualmente, reemplazá al menos `importer/import_catalog.py`, `.github/workflows/update-catalog.yml` y `README.md`.
4. Confirmá/subí los cambios a la rama `main`.
5. Entrá en **Actions → Actualizar catálogo → Run workflow**.
6. Revisá el resultado del workflow. Si algún proveedor devuelve 0 productos, mirá `data/import_report.json`; puede requerir un ajuste específico si cambió el HTML o hay protección anti-bot.

## WhatsApp

Antes de publicar, editá `app.js` y cambiá `WHATSAPP_NUMBER` por tu número internacional sin `+`, espacios ni guiones.

## Publicación en Cloudflare Pages

La salida sigue siendo `data/products.json`, por lo que el frontend existente la consume sin cambios. Framework preset `None`, build command vacío y output directory `/`.
