-- Preguntas del juego "Dato Falso Futbolero" (pipeline/generar_dato_falso.py).
-- opciones: [{texto, qid, verdadera}] — 4 verdaderas y 1 falsa, ya mezcladas.
create table dato_falso_preguntas (
  id            bigserial primary key,
  clave         text not null unique,       -- tipo:protagonista:falsa (evita duplicados)
  tipo          text not null check (tipo in ('clubes_de_jugador', 'jugadores_de_club', 'jugadores_de_pais')),
  dificultad    text not null check (dificultad in ('facil', 'intermedio', 'dificil')),
  afirmacion    text not null,
  protagonista  jsonb not null,             -- {tipo: 'jugador'|'club'|'pais', qid, nombre}
  opciones      jsonb not null,
  explicacion   text not null,
  fuente        text not null default 'generado desde wikidata',
  generado_en   timestamptz not null default now(),
  ejecucion_id  bigint references ejecuciones (id)
);
create index on dato_falso_preguntas (dificultad);

alter table dato_falso_preguntas enable row level security;
create policy "lectura publica" on dato_falso_preguntas for select to anon, authenticated using (true);
grant select on dato_falso_preguntas to anon, authenticated;
