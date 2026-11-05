import { cacheLife, cacheTag } from "next/cache";
import { leerDeSupabase } from "@/lib/supabase";
import type { Puzzle } from "./tipos";

/** Puzzles de Conexiones guardados en Supabase. Se refrescan cada hora. */
export async function leerPuzzles(): Promise<Puzzle[]> {
  "use cache";
  cacheLife("hours");
  cacheTag("conexiones");
  return leerDeSupabase<Puzzle[]>(
    "conexiones_puzzles?select=id,fecha,grupos,trampas&order=fecha.asc",
  );
}
