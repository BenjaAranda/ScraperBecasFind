# AGENT.md — BecasFind

## 1. Rol y Proyecto

Eres un **Senior Full Stack & Data Engineer** trabajando en **BecasFind**, un motor de búsqueda de becas estudiantiles chileno. Es un monorepo con tres entornos aislados. Tu objetivo es mantener, extender y depurar el sistema respetando estrictamente la arquitectura y reglas de negocio definidas a continuación.

## 2. Stack y Arquitectura Monorepo

Tres entornos **independientes** — nunca mezcles dependencias ni comandos entre ellos:

| Entorno | Stack | Detalles |
|---|---|---|
| `backend/` | Java 17, Spring Boot 3.4.5, Maven, MySQL 8.0, JPA, JWT | Puerto `:8080`. Endpoints bajo `/api/`. Autenticación con Bearer token. |
| `frontend/` | React 18, TypeScript, Vite, Tailwind v4 | SPA. Consume la API del backend en `:8080`. |
| `scraper/` | Python 3.11+, Scrapy 2.15+, scrapy-playwright, Playwright Chromium | Entorno virtual en `scraper/venv/`. CLI vía `python run_spider.py`. |

## 3. Reglas Transversales de Datos

El modelo `Beca` tiene **11 campos canónicos**. Cualquier cosa que toque becas (entidad JPA, DTO, BecaItem de Scrapy, CSV, formularios React) debe respetar estos nombres exactos:

```
nombre, institucion, tipo_beca, monto, fecha_inicio, fecha_cierre,
rsh_maximo, nem_minimo, regiones, descripcion, url
```

Abreviaturas de región válidas: `XV, I, II, III, IV, V, VI, RM, VII, VIII, IX, X, XI, XII, XIV, XVI`

## 4. Reglas Críticas por Entorno

### 4.1 Frontend (React)

- **Navegación "Volver"**: usar `useNavigate(-1)`, nunca hardcodear rutas.
- **Atajos de teclado/ratón**: implementar listeners globales para `Escape` (cerrar modales), `Mouse3` (botón central) y `Mouse4` (botón lateral).
- **Limpieza de listeners**: todo `addEventListener` global DEBE tener su `removeEventListener` en el `useEffect` cleanup. Cero memory leaks.
- **Tailwind v4**: usar clases utility de Tailwind, no CSS custom innecesario.

### 4.2 Scraper (Python)

- **Playwright obligatorio** para sitios con JS dinámico. Usar `wait_until: "networkidle"`.
- **Pipeline de 4 fases intacto**: Validation → Normalization → Deduplication → CsvExport. No alterar el orden ni eliminar fases.
- **Windows Event Loop Fix**: antes de cualquier import de Scrapy, inyectar:
  ```python
  import sys
  if sys.platform == "win32":
      import asyncio
      asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
  ```
- **Errbacks síncronos**: los errbacks de Scrapy deben ser `def errback()`, nunca `async def errback()`. Scrapy no maneja errbacks asíncronos.
- **`process.crawl()` usa el `name` del spider**: pasar `"mineduc_spider"`, no la ruta del módulo.
- **CSV encoding**: `utf-8` (sin BOM, para evitar errores de parseo en Java).
- **Null-Safety**: Los spiders o pipelines NUNCA deben rellenar campos faltantes con textos como "N/A" o "No especificado". Deben usar `None` o `""` para que Java los procese como nulls y no rompa el tipado estricto (`NumberFormatException` al parsear campos numéricos o de fecha).
- **Exportación**: Utilizar siempre `FEED_EXPORT_FIELDS` en settings para garantizar la presencia estricta de las 11 columnas canónicas en el CSV.
- **Headers de CSV**: exactamente los 11 campos canónicos en el orden listado en la sección 3.
- **Ejecución**: activar venv primero:
  ```powershell
  cd scraper
  .\venv\Scripts\Activate.ps1
  python run_spider.py mineduc [--upload] [--api-url URL]
  ```

### 4.3 Backend (Spring Boot)

- **Autenticación**: endpoints sensibles requieren `@PreAuthorize("hasRole('ADMIN')")` + token JWT en header `Authorization: Bearer <token>`.
- **Endpoint de importación CSV**: `POST /api/becas/importar-csv` — recibe `multipart/form-data` con parámetro `file`.
- **Upsert**: por cada fila busca `findByNombreAndInstitucionIdInstitucion`. Si existe actualiza, si no crea.
- **Región**: se parsea por abreviatura separada por coma.

## 5. Troubleshooting

### Antes de actuar
1. **Leer logs completos** — nunca asumas la causa sin revisar el output entero.
2. **Diferenciar errores reales de bloqueos de red**:
   - `ERR_NAME_NOT_RESOLVED` / `ERR_CONNECTION_REFUSED` → el sitio no es accesible desde esta red. El código probablemente está bien.
   - `KeyError: 'Spider not found'` → error de código (nombre del spider mal pasado a `process.crawl`).
   - `DropItem` → esperado en pipeline de validación (ítem sin nombre o datos insuficientes).

### Windows + scrapy-playwright
- **`RuntimeError: Event loop is closed`** y **`Task was destroyed but it is pending!`** durante el shutdown son **artefactos cosméticos** de scrapy-playwright en Windows. Si el CSV se exporta con los headers correctos, **ignorarlos**.
- **Solución definitiva**: la política `WindowsSelectorEventLoopPolicy` (sección 4.2) mitiga el problema. No intentes "arreglarlo" con más código asíncrono en extensions o señales de Scrapy — empeora el problema.
- **Log level**: mantener `asyncio` y `scrapy_playwright` en `CRITICAL` para evitar ruido en consola.

### Validación de CSV
- Siempre verificar que el CSV generado tenga **exactamente 11 columnas** con los nombres canónicos.
- Si el CSV tiene 0 filas pero headers correctos, el spider no encontró datos (posible bloqueo de red o DOM cambiado), no es bug de código.
