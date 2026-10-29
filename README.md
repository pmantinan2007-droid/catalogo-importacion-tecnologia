# Catálogo de tecnología — versión de importación revisada

Sitio estático publicado desde GitHub/Cloudflare. El importador intenta leer páginas públicas de Cellshop, Nissei, Madrid Center y Shopping China, extraer productos con nombre, imagen y precio explícito en USD, y aplicar un recargo del 40%.

## Importante
- La publicación del sitio y la extracción de los proveedores son cosas distintas. La estructura de cada tienda puede cambiar y puede requerir integración específica, API o feed autorizado.
- El importador **no inventa precios**. Los precios en guaraníes/reales se omiten hasta configurar una conversión fiable y verificable. Los importes en ARS se calculan únicamente cuando se define la variable `ARS_PER_USD`; no se obtiene automáticamente de DolarHoy todavía.
- No evita CAPTCHA, inicio de sesión ni otras restricciones de acceso.
- El catálogo empieza vacío y no muestra productos de demostración como si fueran reales.

## Publicar cambios en GitHub
1. Descomprimí el ZIP.
2. Abrí tu repositorio en GitHub.
3. Subí/reemplazá `app.js`, `index.html`, `importer/providers.json`, `importer/import_catalog.py`, `data/products.json` y `README.md`, manteniendo exactamente las carpetas.
4. Confirmá con **Commit changes**. Cloudflare debería volver a desplegar el sitio automáticamente.

## Ejecutar la importación
En GitHub, abrí **Actions** → **Actualizar catálogo** → **Run workflow**. Al terminar, revisá el resumen/log del trabajo. Si un proveedor no permite extracción desde su página inicial, hay que adaptar su integración.

## Configurar tipo de cambio
En el repositorio: **Settings → Secrets and variables → Actions → Variables → New repository variable**.
- Name: `ARS_PER_USD`
- Value: cotización en pesos por dólar que hayas verificado ese día.

El workflow no consulta DolarHoy automáticamente todavía; esta variable debe actualizarse manualmente hasta conectar una fuente de cotización fiable.

## WhatsApp
En `app.js`, reemplazá `WHATSAPP_NUMBER` por el número real en formato internacional, solo dígitos y sin `+`, espacios ni guiones.
