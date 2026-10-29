# NEXO TECH — actualización de imágenes y cotizaciones

Este parche conserva el diseño actual y actualiza únicamente el importador y el catálogo de datos.

## Qué hace
- Revisa las fichas de producto ya guardadas y completa `image_url` con `og:image`, Twitter Card, JSON-LD y galerías de producto.
- En productos que exponen precio en JSON-LD, vuelve a leer el precio de la ficha y actualiza el precio de origen.
- Convierte PYG y BRL a USD con la tasa de referencia pública USD del día; agrega 40% de margen una sola vez.
- Para ARS intenta obtener el dólar blue vendedor de DolarHoy. Si no logra leerlo, utiliza la tasa USD/ARS de respaldo de la API de cambio y lo identifica explícitamente en `ars_source`. Se puede forzar el respaldo manual con la variable `ARS_PER_USD`.
- Recalcula el equivalente en pesos en cada ejecución. No inventa URLs de imágenes ni precios que no haya podido leer.
- El informe `data/import_report.json` ahora incluye `products_with_images` y `products_without_images`.

## Archivos a reemplazar en el repositorio existente
1. `importer/import_catalog.py`
2. `README.md` (opcional, solo documentación)

No reemplazar `data/products.json`: el importador conserva los productos que ya aparecen en la web y completa sus imágenes desde sus fichas originales. No reemplazar `index.html`, `styles.css` ni `app.js`.

Después del commit, ejecutar **Actions → Actualizar catálogo → Run workflow**. Esperar que finalice y revisar `data/import_report.json`.

## Sobre precios
La fórmula es: precio origen convertido a USD × 1,40. Luego precio USD × cotización ARS/USD. Para PYG, se usa la tasa PYG por USD de la API de cambio. Para ARS, se prioriza DolarHoy (dólar blue vendedor); si la lectura falla, el informe deja identificada la fuente de respaldo. Los importes del proveedor se consideran referencias y deben confirmarse con el comercio antes de vender. Si una ficha no expone precio estructurado, se conserva el último precio conocido y no se lo presenta como recién verificado.

## Limitación real
La descarga de imágenes depende de que el proveedor permita acceder a su ficha y de que la URL de imagen sea pública. Si el proveedor bloquea la automatización o requiere JavaScript, el informe lo reflejará; no se crean imágenes falsas ni URLs inventadas.
