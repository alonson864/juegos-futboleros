import { cacheLife, cacheTag } from "next/cache";
import { leerDeSupabase } from "@/lib/supabase";
import type { Pregunta } from "./tipos";

/** Preguntas de Dato Falso guardadas en Supabase. Se refrescan cada hora. */
export async function leerPreguntas(): Promise<Pregunta[]> {
  "use cache";
  cacheLife("hours");
  cacheTag("dato-falso");
  return leerDeSupabase<Pregunta[]>(
    "dato_falso_preguntas?select=id,tipo,dificultad,afirmacion,opciones,explicacion,protagonista&order=id.asc",
  );
}
