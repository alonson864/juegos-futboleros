@AGENTS.md

# Reglas del proyecto: Juegos Futboleros

- Todo el texto de la página va en español neutro latinoamericano.
- La primera versión es para laptop/computadora (pantallas de 1280-1440px): ahí debe verse y jugarse mejor.
  El celular (375px de ancho) se mantiene funcionando: los estilos base son para celular y los de laptop van con el prefijo `lg:`.
- Cada juego vive en su propia carpeta: `src/app/juegos/<nombre-del-juego>` (el proyecto usa la carpeta `src/`).

## Datos

- La fuente de datos del proyecto es una base en Supabase. Todos los juegos deben sacar sus datos (jugadores, clubes, puzzles) de esa base, nunca escritos dentro del código.
- Ningún dato futbolístico puede salir de la memoria de la IA: todo viene de fuentes externas públicas y gratuitas (Wikidata, Wikipedia en inglés y Wikimedia Commons) mediante código en `pipeline/` (Python).
- Lo que viene de Wikipedia tiene licencia CC BY-SA 4.0: el sitio debe mostrar siempre el crédito (está en el pie de página).
- Cada dato guarda su fuente y su fecha de actualización. La tabla de correcciones manuales siempre tiene prioridad sobre lo que trae el pipeline.
- `data/conexiones.json` son datos de prueba hechos a mano; se van a reemplazar por datos de la base.
- Las claves de Supabase van en `.env` (nunca en git).

## Imágenes

- Fotos de jugadores: solo de Wikimedia Commons con licencia libre (CC0, dominio público, CC BY, CC BY-SA), mostrando siempre autor y licencia. Si no hay foto válida, avatar genérico.
- No uses escudos oficiales de clubes (son marcas registradas).

## Librerías

- No agregues librerías nuevas sin preguntarme primero.
- Ya aprobadas: `requests`, `supabase` (Python), `psycopg`, `python-dotenv`, `@supabase/supabase-js`.
- El pipeline usa Python 3.12 en `pipeline/.venv`. Las tablas se crean con migraciones en `pipeline/migraciones/` (`pipeline/migrar.py`).
- Orden del pipeline (cada paso se puede repetir sin duplicar nada): `migrar.py` → `paso1_clubes` → `paso2_jugadores --incremental` → `paso2b_nombres` → `paso2c_paises` → `paso2d_nombres_lusofonos` → `paso2e_nombres_consenso` (2d y 2e después de 2b, que si no pisa estos nombres) → `paso7_fama` → `paso4_wikipedia` → `paso5_torneos_premios` → `paso6_participaciones` → `paso3_fotos` → `paso8_calidad` → generadores (`generar_conexiones --regenerar`, `generar_dato_falso`, `generar_ultimo_en_pie`, `generar_buscaminas`).
- Para corridas largas usar `caffeinate -i -s` (si la Mac se duerme, se cortan las consultas).

## Al terminar

- Antes de decir que terminaste, corre `npm run build` y arregla cualquier error.
- Explica en 2 o 3 líneas simples qué cambiaste.
