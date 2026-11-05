-- Datos de Wikipedia (en inglés, CC BY-SA 4.0) de los jugadores más relevantes,
-- y torneos/premios con sus ediciones.

-- Competiciones y premios que aparecen en los palmarés
create table competiciones (
  qid             text primary key,
  nombre          text not null,           -- en español si Wikidata lo tiene
  articulo_en     text,                    -- título del artículo en Wikipedia en inglés
  relevante       boolean not null default false,  -- las que usan los juegos (Champions, Mundial, Balón de Oro…)
  tipo            text not null default 'otro'
                  check (tipo in ('torneo_clubes', 'torneo_selecciones', 'premio', 'otro')),
  fuente          text not null default 'wikipedia_en+wikidata',
  actualizado_en  timestamptz not null default now()
);

-- Ediciones de cada competición, con su campeón
create table ediciones (
  qid              text primary key,
  competicion_qid  text references competiciones (qid) on delete cascade,
  nombre           text not null,
  anio             integer,                -- año en que terminó (2005–06 -> 2006)
  temporada        text,                   -- como la escribe la fuente: "2005–06", "2014"
  campeon_qid      text,                   -- club, selección o jugador
  campeon_nombre   text,
  fuente           text not null default 'wikidata',
  actualizado_en   timestamptz not null default now()
);
create index on ediciones (competicion_qid);

-- Información del artículo de Wikipedia de cada jugador
create table jugadores_wikipedia (
  jugador_qid       text primary key references jugadores (qid) on delete cascade,
  articulo          text not null,
  revision          bigint not null,       -- número de revisión leído (para saber si cambió)
  fecha_revision    timestamptz,
  al_dia_clubes     text,                  -- "al día" según el propio artículo
  al_dia_seleccion  text,
  fuente            text not null default 'wikipedia_en',
  actualizado_en    timestamptz not null default now()
);

-- Carrera según la ficha de Wikipedia (partidos y goles por equipo)
create table carrera_wikipedia (
  jugador_qid     text not null references jugadores (qid) on delete cascade,
  seleccion       boolean not null,
  orden           integer not null,
  equipo_qid      text,
  equipo_texto    text not null,
  prestamo        boolean not null default false,
  desde           integer,
  hasta           integer,
  partidos        integer,
  goles           integer,
  fuente          text not null default 'wikipedia_en',
  actualizado_en  timestamptz not null default now(),
  primary key (jugador_qid, seleccion, orden)
);

-- Títulos y premios de cada jugador según su palmarés en Wikipedia
create table titulos_jugador (
  id                 text primary key,     -- jugador|competición|edición (o año)
  jugador_qid        text not null references jugadores (qid) on delete cascade,
  competicion_qid    text,
  competicion_texto  text not null,        -- como aparece en el palmarés
  edicion_qid        text,
  temporada          text,
  anio               integer,
  grupo              text,                 -- club o selección con que lo ganó, o "Individual"
  individual         boolean not null default false,
  fuente             text not null default 'wikipedia_en',
  revision           bigint,
  actualizado_en     timestamptz not null default now()
);
create index on titulos_jugador (jugador_qid);
create index on titulos_jugador (competicion_qid);

-- Las correcciones manuales también pueden tocar estas tablas
alter table correcciones drop constraint correcciones_tabla_check;
alter table correcciones add constraint correcciones_tabla_check
  check (tabla in ('jugadores', 'clubes', 'pasos_por_club', 'imagenes',
                   'titulos_jugador', 'carrera_wikipedia', 'ediciones'));

create view titulos_jugador_final with (security_invoker = true) as
select r.*
from titulos_jugador t
cross join lateral jsonb_populate_record(
          t,
          coalesce((select jsonb_object_agg(c.campo, c.valor)
                    from correcciones c
                    where c.tabla = 'titulos_jugador' and c.registro = t.id and c.campo <> '_excluir'),
                   '{}'::jsonb)
       ) r
where not exists (select 1 from correcciones c
                  where c.tabla = 'titulos_jugador' and c.registro = t.id and c.campo = '_excluir');

create view ediciones_final with (security_invoker = true) as
select r.*
from ediciones t
cross join lateral jsonb_populate_record(
          t,
          coalesce((select jsonb_object_agg(c.campo, c.valor)
                    from correcciones c
                    where c.tabla = 'ediciones' and c.registro = t.qid and c.campo <> '_excluir'),
                   '{}'::jsonb)
       ) r
where not exists (select 1 from correcciones c
                  where c.tabla = 'ediciones' and c.registro = t.qid and c.campo = '_excluir');

do $$
declare
  t text;
begin
  foreach t in array array['competiciones', 'ediciones', 'jugadores_wikipedia', 'carrera_wikipedia', 'titulos_jugador']
  loop
    execute format('alter table %I enable row level security', t);
    execute format('create policy "lectura publica" on %I for select to anon, authenticated using (true)', t);
    execute format('grant select on %I to anon, authenticated', t);
  end loop;
end
$$;
grant select on titulos_jugador_final, ediciones_final to anon, authenticated;
