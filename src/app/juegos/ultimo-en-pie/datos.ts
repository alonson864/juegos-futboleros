import { cacheLife, cacheTag } from "next/cache";
import { leerDeSupabase } from "@/lib/supabase";
import type { Categoria } from "./tipos";

/** Categorías de "Último en pie" guardadas en Supabase. Se refrescan cada hora. */
export async function leerCategorias(): Promise<Categoria[]> {
  "use cache";
  cacheLife("hours");
  cacheTag("ultimo-en-pie");
  return leerDeSupabase<Categoria[]>(
    "ultimo_en_pie_categorias?select=id,titulo,dificultad,cantidad,miembros_destacados&order=id.asc",
  );
}
