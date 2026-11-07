-- Juego "Mayor o menor".
-- Dos listas que vienen de tablas de Wikipedia en inglés (CC BY-SA 4.0), leídas por
-- pipeline/paso9_listas_wikipedia.py, y los jugadores listos para el juego
-- (pipeline/generar_mayor_menor.py).

-- Fichajes más caros de la historia ("List of most expensive association football transfers")
create table fichajes (
  id              text primary key,         -- jugador|origen|destino|año
  jugador_qid     text references jugadores (qid) on delete cascade,
  jugador_texto   text not null,
  origen          text not null,
  destino         text not null,
  monto_eur       numeric not null,         -- millones de euros, como los indica el artículo
  anio            integer,
  articulo        text not null,
  revision        bigint not null,
  fuente          text not null default 'wikipedia_en',
  actualizado_en  timestamptz not null default now()
);

-- Máximos asistidores de una competición ("Premier League records and statistics")
create table asistencias (
  id              text primary key,         -- competición|jugador
  jugador_qid     text references jugadores (qid) on delete cascade,
  jugador_texto   text not null,
  competicion     text not null,
  asistencias     integer not null,
  partidos        integer,
  articulo        text not null,
  revision        bigint not null,
  fuente          text not null default 'wikipedia_en',
  actualizado_en  timestamptz not null default now()
);

-- Jugadores de cada categoría del juego, con su número
create table mayor_menor_jugadores (
  id              text primary key,         -- categoría|clave
  categoria       text not null check (categoria in ('goles', 'asistencias', 'titulos', 'fichajes', 'partidos')),
  jugador_qid     text not null,
  nombre          text not null,
  valor           numeric not null,
  detalle         text,                     -- p. ej. "Barcelona → Paris Saint-Germain (2017)"
  foto            jsonb,
  fuente          text not null,
  generado_en     timestamptz not null default now()
);
create index on mayor_menor_jugadores (categoria);

alter table fichajes enable row level security;
alter table asistencias enable row level security;
alter table mayor_menor_jugadores enable row level security;
create policy "lectura publica" on fichajes for select to anon, authenticated using (true);
create policy "lectura publica" on asistencias for select to anon, authenticated using (true);
create policy "lectura publica" on mayor_menor_jugadores for select to anon, authenticated using (true);
grant select on fichajes, asistencias, mayor_menor_jugadores to anon, authenticated;
