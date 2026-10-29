
# Catálogo de importación de tecnología — versión inicial

Proyecto inicial para una web de catálogo con diseño oscuro/azul, precios USD/ARS, búsqueda, categorías, productos destacados y consultas por WhatsApp.

## Importante: qué hace y qué no hace esta versión

- La web pública funciona con `data/products.json`.
- El importador Python intenta obtener productos desde páginas públicas mediante JSON-LD (`Product`) y metadatos Open Graph.
- Cada proveedor tiene configuración separada en `importer/providers.json`.
- Se guardan URL de origen, precio, moneda, fotografía, proveedor y fecha de consulta.
- El precio de venta aplica un recargo del 40% al precio base USD.
- El tipo de cambio ARS/USD se configura mediante `ARS_PER_USD` en GitHub Secrets/Variables o en el entorno.
- La importación debe probarse y ajustarse proveedor por proveedor. Las tiendas pueden usar JavaScript, paginación, protección anti-bot, monedas/precios regionales o restricciones de reutilización de contenido. **No se garantiza que el importador inicial extraiga el catálogo completo de los cuatro sitios sin ajustes.**
- No se copian imágenes a un servidor propio: se guardan sus URLs cuando están disponibles. Verificá permisos/condiciones de uso con cada proveedor.
- DolarHoy no se consulta todavía automáticamente porque la página puede cambiar su estructura. Para evitar publicar precios incorrectos, el tipo de cambio es una variable configurable. Se puede añadir un conector verificado después de probar la fuente actual.

## Probar en tu computadora

Requiere Python 3.11+.

```bash
pip install -r requirements.txt
python importer/import_catalog.py
```

Por defecto consulta una selección pequeña de URLs de categoría configuradas en `importer/providers.json`. Para importar más páginas, agregá URLs de categorías públicas y aumentá `max_pages` con prudencia.

Después abrí `index.html` en un navegador. Para que `fetch()` funcione correctamente, es mejor iniciar un servidor local:

```bash
python -m http.server 8000
```

Y abrí `http://localhost:8000`.

## Configurar WhatsApp

Editá `app.js` y cambiá `WHATSAPP_NUMBER` por tu número internacional sin `+`, espacios ni guiones. Ejemplo: `54911XXXXXXXX`.

## Publicar gratis

1. Creá un repositorio GitHub y subí los archivos.
2. En Cloudflare Pages, conectá el repositorio.
3. Framework preset: `None`; build command vacío; output directory `/`.
4. Para ejecutar el importador periódicamente, configurá GitHub Actions.
5. En GitHub → Settings → Secrets and variables → Actions, agregá:
   - `ARS_PER_USD`: cotización ARS por USD que hayas verificado.
6. Activá Actions y ejecutá `Actualizar catálogo` manualmente para la primera prueba.

## Uso responsable

Consultá los términos de cada proveedor y obtené autorización cuando corresponda antes de extraer o republicar descripciones e imágenes. No eludas CAPTCHA, login, bloqueos ni controles de acceso. Los precios y el stock deben confirmarse con el proveedor antes de aceptar un pedido.

## Próximos pasos técnicos

1. Probar cada proveedor y validar resultados reales.
2. Ajustar selectores/endpoints por tienda y paginación.
3. Verificar la cotización de DolarHoy y su política de uso.
4. Incorporar almacenamiento de imágenes propio únicamente si existe autorización.
5. Si el catálogo crece, mover datos de JSON a una base de datos y añadir panel administrativo protegido.
