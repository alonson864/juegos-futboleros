-- Continente y gentilicio de cada país (Wikidata P30 y P1549), para categorías como
-- "Sudamericanos que jugaron en…" o "Argentinos que jugaron en…".
alter table paises
  add column continente_qid text,
  add column continente text,
  add column gentilicio text;    -- masculino singular, como lo da Wikidata ("argentino")
