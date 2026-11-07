import { cacheLife, cacheTag } from "next/cache";
import { leerDeSupabase } from "@/lib/supabase";
import type { Item } from "./tipos";

/** Jugadores de cada categoría de Mayor o menor, guardados en Supabase. Se refrescan cada hora. */
export async function leerItems(): Promise<Item[]> {
  "use cache";
  cacheLife("hours");
  cacheTag("mayor-o-menor");
  const items = await leerDeSupabase<Item[]>(
    "mayor_menor_jugadores?select=id,categoria,jugador_qid,nombre,valor,detalle,foto&order=id.asc&limit=5000",
  );
  return items.map((i) => ({ ...i, valor: Number(i.valor) }));
}
