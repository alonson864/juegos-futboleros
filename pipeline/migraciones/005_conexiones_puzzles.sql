-- Puzzles de Conexiones generados desde la base (pipeline/generar_conexiones.py).
-- grupos: [{categoria, dificultad (1-4), jugadores: [nombres], jugadores_qid: [códigos]}]
-- trampas: ["Fulano también jugó en ...", ...]
create table conexiones_puzzles (
  id              bigserial primary key,
  fecha           date not null unique,
  grupos          jsonb not null,
  trampas         jsonb not null default '[]',
  fuente          text not null default 'generado desde wikidata',
  generado_en     timestamptz not null default now(),
  ejecucion_id    bigint references ejecuciones (id)
);

alter table conexiones_puzzles enable row level security;
create policy "lectura publica" on conexiones_puzzles for select to anon, authenticated using (true);
grant select on conexiones_puzzles to anon, authenticated;
