-- Búsqueda de jugadores por nombre (sin tildes, con apodos y nombres en otros idiomas)
alter table jugadores add column busqueda text;
create extension if not exists pg_trgm;
create index jugadores_busqueda_trgm on jugadores using gin (busqueda gin_trgm_ops);

-- La vista debe incluir la columna nueva (las vistas fijan sus columnas al crearse)
create or replace view jugadores_final with (security_invoker = true) as
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

-- Categorías del juego "Último en pie" (pipeline/generar_ultimo_en_pie.py)
-- parametros: {tipo: 'club'|'clubes'|'seleccion'|'titulo', ...códigos para verificar}
create table ultimo_en_pie_categorias (
  id                    bigserial primary key,
  clave                 text not null unique,
  titulo                text not null,
  parametros            jsonb not null,
  cantidad              integer not null,        -- jugadores conocidos que cumplen
  miembros_destacados   jsonb not null,          -- algunos que cumplen (para mostrar al final de la ronda)
  dificultad            text not null check (dificultad in ('facil', 'intermedio', 'dificil')),
  fuente                text not null default 'generado desde wikidata+wikipedia',
  generado_en           timestamptz not null default now()
);

alter table ultimo_en_pie_categorias enable row level security;
create policy "lectura publica" on ultimo_en_pie_categorias for select to anon, authenticated using (true);
grant select on ultimo_en_pie_categorias to anon, authenticated;
