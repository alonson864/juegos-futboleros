-- Tipos nuevos de pregunta en Dato Falso: títulos y premios.
alter table dato_falso_preguntas drop constraint dato_falso_preguntas_tipo_check;
alter table dato_falso_preguntas add constraint dato_falso_preguntas_tipo_check
  check (tipo in ('clubes_de_jugador', 'jugadores_de_club', 'jugadores_de_pais',
                  'ganadores_de_titulo', 'equipos_campeones', 'titulos_de_jugador'));
