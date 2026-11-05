-- Fama real: visitas al artículo del jugador en Wikipedia (inglés + español) en los últimos 12 meses.
alter table jugadores add column visitas integer;
create index on jugadores (visitas desc nulls last);

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
