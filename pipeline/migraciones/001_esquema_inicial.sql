-- Esquema inicial de la base de jugadores.
-- Lo aplica pipeline/migrar.py una sola vez (queda registrado en migraciones_aplicadas).

-- ---------------------------------------------------------------------------
-- Registro de cada vez que corre el pipeline y de lo que cambió
-- ---------------------------------------------------------------------------
create table ejecuciones (
  id            bigserial primary key,
  iniciada_en   timestamptz not null default now(),
  terminada_en  timestamptz,
  estado        text not null default 'en_curso'
                check (estado in ('en_curso', 'ok', 'error')),
  resumen       jsonb
);

create table cambios (
  id            bigserial primary key,
  ejecucion_id  bigint not null references ejecuciones (id) on delete cascade,
  tabla         text not null,
  registro      text not null,
  tipo          text not null check (tipo in ('nuevo', 'modificado', 'eliminado')),
  detalle       jsonb
);
create index on cambios (ejecucion_id);

-- ---------------------------------------------------------------------------
-- Catálogos: ligas, países y posiciones (códigos de Wikidata)
-- ---------------------------------------------------------------------------
create table ligas (
  qid             text primary key,
  nombre          text not null,
  pais            text,
  fuente          text not null default 'wikidata',
  actualizado_en  timestamptz not null default now()
);

create table paises (
  qid             text primary key,
  nombre          text not null,
  fuente          text not null default 'wikidata',
  actualizado_en  timestamptz not null default now()
);

create table posiciones (
  qid             text primary key,
  nombre          text not null,
  fuente          text not null default 'wikidata',
  actualizado_en  timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Clubes (incluye selecciones y equipos juveniles, separados por "tipo")
-- ---------------------------------------------------------------------------
create table clubes (
  qid               text primary key,
  nombre            text not null,
  pais_qid          text references paises (qid),
  tipo              text not null default 'desconocido'
                    check (tipo in ('club', 'seleccion', 'seleccion_juvenil', 'juvenil', 'desconocido')),
  fuente            text not null default 'wikidata',
  actualizado_en    timestamptz not null default now(),
  ultima_ejecucion  bigint references ejecuciones (id)
);

-- Qué clubes pertenecen (o pertenecieron) a qué liga
create table clubes_ligas (
  club_qid        text not null references clubes (qid) on delete cascade,
  liga_qid        text not null references ligas (qid) on delete cascade,
  inicio          date,
  fin             date,
  fuente          text not null default 'wikidata',
  actualizado_en  timestamptz not null default now(),
  primary key (club_qid, liga_qid)
);

-- ---------------------------------------------------------------------------
-- Jugadores
-- ---------------------------------------------------------------------------
create table jugadores (
  qid                   text primary key,
  nombre                text not null,
  fecha_nacimiento      date,
  -- Precisión de Wikidata: 9 = solo año, 10 = año y mes, 11 = día exacto
  precision_nacimiento  smallint,
  nacionalidades        text[] not null default '{}',   -- códigos de países
  posiciones            text[] not null default '{}',   -- códigos de posiciones
  popularidad           integer not null default 0,     -- número de Wikipedias con artículo
  huella                text,                           -- resumen de los datos para detectar cambios
  fuente                text not null default 'wikidata',
  actualizado_en        timestamptz not null default now(),
  ultima_ejecucion      bigint references ejecuciones (id)
);
create index on jugadores (popularidad desc);

-- Cada paso de un jugador por un club. La clave es el identificador del dato
-- en Wikidata, así que volver a correr el pipeline nunca lo duplica.
create table pasos_por_club (
  id_wikidata       text primary key,
  jugador_qid       text not null references jugadores (qid) on delete cascade,
  club_qid          text not null references clubes (qid),
  inicio            date,
  inicio_precision  smallint,
  fin               date,
  fin_precision     smallint,
  partidos          integer,
  goles             integer,
  fuente            text not null default 'wikidata',
  actualizado_en    timestamptz not null default now(),
  ultima_ejecucion  bigint references ejecuciones (id)
);
create index on pasos_por_club (jugador_qid);
create index on pasos_por_club (club_qid);

-- ---------------------------------------------------------------------------
-- Fotos (solo Wikimedia Commons, con autor y licencia)
-- ---------------------------------------------------------------------------
create table imagenes (
  jugador_qid       text primary key references jugadores (qid) on delete cascade,
  archivo           text not null,     -- nombre del archivo en Commons
  url               text,
  url_miniatura     text,
  autor             text,
  licencia          text,
  licencia_url      text,
  licencia_libre    boolean not null default false,  -- solo se muestran las libres
  fuente            text not null default 'wikimedia_commons',
  actualizado_en    timestamptz not null default now(),
  ultima_ejecucion  bigint references ejecuciones (id)
);

-- ---------------------------------------------------------------------------
-- Correcciones manuales: siempre ganan sobre lo que trae el pipeline.
-- campo = nombre de la columna a corregir, o '_excluir' para ocultar el registro.
-- valor = valor correcto en JSON (por ejemplo "Ronaldinho" o "1980-03-21").
-- ---------------------------------------------------------------------------
create table correcciones (
  id         bigserial primary key,
  tabla      text not null check (tabla in ('jugadores', 'clubes', 'pasos_por_club', 'imagenes')),
  registro   text not null,   -- qid del jugador/club, o id_wikidata del paso
  campo      text not null,
  valor      jsonb,
  motivo     text not null,
  creado_en  timestamptz not null default now(),
  unique (tabla, registro, campo)
);

-- ---------------------------------------------------------------------------
-- Vistas "_final": datos del pipeline con las correcciones aplicadas.
-- Los juegos deben leer siempre estas vistas, nunca las tablas directamente.
-- ---------------------------------------------------------------------------
create view jugadores_final with (security_invoker = true) as
select r.*
from jugadores t
cross join lateral jsonb_populate_record(
          t,
          coalesce((select jsonb_object_agg(c.campo, c.valor)
                    from correcciones c
                    where c.tabla = 'jugadores' and c.registro = t.qid and c.campo <> '_excluir'),
                   '{}'::jsonb)
       ) r
where not exists (select 1 from correcciones c
                  where c.tabla = 'jugadores' and c.registro = t.qid and c.campo = '_excluir');

create view clubes_final with (security_invoker = true) as
select r.*
from clubes t
cross join lateral jsonb_populate_record(
          t,
          coalesce((select jsonb_object_agg(c.campo, c.valor)
                    from correcciones c
                    where c.tabla = 'clubes' and c.registro = t.qid and c.campo <> '_excluir'),
                   '{}'::jsonb)
       ) r
where not exists (select 1 from correcciones c
                  where c.tabla = 'clubes' and c.registro = t.qid and c.campo = '_excluir');

create view pasos_por_club_final with (security_invoker = true) as
select r.*
from pasos_por_club t
cross join lateral jsonb_populate_record(
          t,
          coalesce((select jsonb_object_agg(c.campo, c.valor)
                    from correcciones c
                    where c.tabla = 'pasos_por_club' and c.registro = t.id_wikidata and c.campo <> '_excluir'),
                   '{}'::jsonb)
       ) r
where not exists (select 1 from correcciones c
                  where c.tabla = 'pasos_por_club' and c.registro = t.id_wikidata and c.campo = '_excluir');

create view imagenes_final with (security_invoker = true) as
select r.*
from imagenes t
cross join lateral jsonb_populate_record(
          t,
          coalesce((select jsonb_object_agg(c.campo, c.valor)
                    from correcciones c
                    where c.tabla = 'imagenes' and c.registro = t.jugador_qid and c.campo <> '_excluir'),
                   '{}'::jsonb)
       ) r
where not exists (select 1 from correcciones c
                  where c.tabla = 'imagenes' and c.registro = t.jugador_qid and c.campo = '_excluir');

-- ---------------------------------------------------------------------------
-- Seguridad: la página web (clave publishable) solo puede LEER los datos.
-- El pipeline escribe con la conexión directa a la base, que no pasa por aquí.
-- ejecuciones y cambios quedan privados.
-- ---------------------------------------------------------------------------
do $$
declare
  t text;
begin
  foreach t in array array['ejecuciones', 'cambios', 'ligas', 'paises', 'posiciones', 'clubes',
                           'clubes_ligas', 'jugadores', 'pasos_por_club', 'imagenes', 'correcciones']
  loop
    execute format('alter table %I enable row level security', t);
  end loop;

  foreach t in array array['ligas', 'paises', 'posiciones', 'clubes', 'clubes_ligas', 'jugadores',
                           'pasos_por_club', 'imagenes', 'correcciones']
  loop
    execute format('create policy "lectura publica" on %I for select to anon, authenticated using (true)', t);
    execute format('grant select on %I to anon, authenticated', t);
  end loop;

  foreach t in array array['ejecuciones', 'cambios']
  loop
    execute format('revoke all on %I from anon, authenticated', t);
  end loop;
end
$$;

grant select on jugadores_final, clubes_final, pasos_por_club_final, imagenes_final to anon, authenticated;
