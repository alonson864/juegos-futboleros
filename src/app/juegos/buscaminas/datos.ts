import { cacheLife, cacheTag } from "next/cache";
import { leerDeSupabase } from "@/lib/supabase";
import type { Ronda } from "./tipos";

/** Rondas de Buscaminas guardadas en Supabase. Se refrescan cada hora. */
export async function leerRondas(): Promise<Ronda[]> {
  "use cache";
  cacheLife("hours");
  cacheTag("buscaminas");
  return leerDeSupabase<Ronda[]>("buscaminas_rondas?select=id,categoria,titulo,dificultad,fichas,explicacion&order=id.asc");
}
