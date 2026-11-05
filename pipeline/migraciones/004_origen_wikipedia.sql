-- El origen de la relación club-liga ahora puede combinar varias fuentes,
-- por ejemplo 'club+temporadas' o 'wikipedia'.
alter table clubes_ligas drop constraint clubes_ligas_origen_check;
update clubes_ligas set origen = 'club+temporadas' where origen = 'ambos';
alter table clubes_ligas add constraint clubes_ligas_origen_check
  check (origen ~ '^(club|temporadas|wikipedia)(\+(club|temporadas|wikipedia))*$');
