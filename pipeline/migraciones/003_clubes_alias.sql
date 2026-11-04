-- Fichas de Wikidata que representan al mismo club.
-- Ejemplo: en Alemania, "primer equipo masculino de 1. FC Köln" es una ficha
-- distinta del club "1. FC Köln". Los jugadores pueden figurar en cualquiera de
-- las dos, así que el pipeline las trata como un solo club.
create table clubes_alias (
  qid             text primary key,      -- ficha del equipo
  club_qid        text not null references clubes (qid) on delete cascade,
  motivo          text not null,         -- 'P361' (forma parte de) o 'P527' (tiene como parte)
  fuente          text not null default 'wikidata',
  actualizado_en  timestamptz not null default now()
);
create index on clubes_alias (club_qid);

alter table clubes_alias enable row level security;
create policy "lectura publica" on clubes_alias for select to anon, authenticated using (true);
grant select on clubes_alias to anon, authenticated;
