-- Jugadores que participaron en cada edición de un torneo (Wikidata P1344 "participó en").
-- No dice con qué selección: eso se deduce de las selecciones del jugador.
create table participaciones (
  jugador_qid      text not null references jugadores (qid) on delete cascade,
  edicion_qid      text not null references ediciones (qid) on delete cascade,
  competicion_qid  text not null,
  anio             integer,
  fuente           text not null default 'wikidata',
  actualizado_en   timestamptz not null default now(),
  primary key (jugador_qid, edicion_qid)
);
create index on participaciones (competicion_qid);

alter table participaciones enable row level security;
create policy "lectura publica" on participaciones for select to anon, authenticated using (true);
grant select on participaciones to anon, authenticated;
