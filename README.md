# NEXO TECH — corrección urgente del catálogo

## Qué incluye
- `data/products.json`: catálogo inicial con 13 productos encontrados en páginas públicas de los cuatro proveedores. Los precios son referencias capturadas el 29/10/2026, con margen del 40%; confirmar antes de vender. Las imágenes quedan pendientes cuando el proveedor no permite extraerlas.
- `importer/import_catalog.py`: importador con rutas de categorías reales de los sitios, más extracción de imágenes `srcset`/lazy-load, reconocimiento de precios con `$`, y fusión de resultados para que un bloqueo no borre productos que ya están publicados.
- El sitio estático original, sin cambiar su diseño.

## Aplicar al repositorio existente
No subas una carpeta anidada ni cambies todo el diseño. En el repositorio de GitHub reemplazá estos dos archivos por los del ZIP:
1. `data/products.json`
2. `importer/import_catalog.py`

Hacé commit de los cambios. Luego ejecutá `Actions → Actualizar catálogo → Run workflow`.

## Importante
`Success` de GitHub Actions solo indica que el trabajo terminó sin error fatal. Mirá `data/import_report.json` y revisá `total_products_extracted` (productos nuevos detectados en esa ejecución) y `total_products_in_catalog` (productos que quedan visibles). Si un proveedor bloquea el acceso, el catálogo previo se conserva.

Los sitios pueden cambiar su HTML o bloquear robots. Este parche evita que la web vuelva a quedar vacía y mejora la extracción, pero no puede garantizar que los cuatro proveedores permitan una importación automática completa en cada ejecución.

## Configuración
- Margen: `MARGIN_PERCENT=40` en el workflow.
- Dólar ARS: el importador intenta leer una cotización pública; si falla, configurar `ARS_PER_USD` en GitHub → Settings → Secrets and variables → Actions → Variables.
- WhatsApp: en `app.js`, cambiar `WHATSAPP_NUMBER` por el número internacional correcto antes de recibir consultas.
