-- Rondas del juego "Buscaminas" (pipeline/generar_buscaminas.py).
-- fichas: [{qid, nombre, cumple, foto?}] — 12 que cumplen y 4 impostores, mezcladas.
create table buscaminas_rondas (
  id            bigserial primary key,
  clave         text not null unique,       -- categoría#versión
  categoria     text not null,              -- para no repetir la misma categoría en una partida
  titulo        text not null,
  dificultad    text not null check (dificultad in ('facil', 'intermedio', 'dificil')),
  fichas        jsonb not null,
  explicacion   text not null,
  fuente        text not null default 'generado desde wikidata+wikipedia',
  generado_en   timestamptz not null default now()
);
alter table buscaminas_rondas enable row level security;
create policy "lectura publica" on buscaminas_rondas for select to anon, authenticated using (true);
grant select on buscaminas_rondas to anon, authenticated;
