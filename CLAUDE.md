@AGENTS.md

# Reglas del proyecto: Juegos Futboleros

- Todo el texto de la página va en español neutro latinoamericano.
- Diseño mobile-first: todo debe verse y jugarse bien en un celular de 375px de ancho.
- Cada juego vive en su propia carpeta: `src/app/juegos/<nombre-del-juego>` (el proyecto usa la carpeta `src/`).

## Datos

- La fuente de datos del proyecto es una base en Supabase. Todos los juegos deben sacar sus datos (jugadores, clubes, puzzles) de esa base, nunca escritos dentro del código.
- Ningún dato futbolístico puede salir de la memoria de la IA: todo viene de fuentes externas públicas y gratuitas (por ahora Wikidata y Wikimedia Commons) mediante código en `pipeline/` (Python).
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

## Al terminar

- Antes de decir que terminaste, corre `npm run build` y arregla cualquier error.
- Explica en 2 o 3 líneas simples qué cambiaste.
