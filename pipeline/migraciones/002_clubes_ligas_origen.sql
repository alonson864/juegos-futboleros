-- De dónde sale que un club estuvo en una liga, y en cuántas temporadas.
alter table clubes_ligas
  add column origen text not null default 'club'
    check (origen in ('club', 'temporadas', 'ambos')),
  add column temporadas integer;

-- Qué paso del pipeline corrió en cada ejecución.
alter table ejecuciones add column paso text;
