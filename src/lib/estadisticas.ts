import { cacheLife, cacheTag } from "next/cache";

export type Estadisticas = {
  jugadores: number;
  clubes: number;
  ediciones: number;
  titulos: number;
};

/** Cuenta filas de una tabla en Supabase sin traerlas (encabezado Content-Range). */
async function contar(ruta: string): Promise<number> {
  const url = process.env.SUPABASE_URL;
  const clave = process.env.SUPABASE_PUBLISHABLE_KEY;
  if (!url || !clave) throw new Error("Faltan las variables de Supabase.");
  const r = await fetch(`${url}/rest/v1/${ruta}`, {
    method: "HEAD",
    headers: { apikey: clave, Prefer: "count=exact" },
  });
  const total = r.headers.get("content-range")?.split("/")[1];
  if (!r.ok || !total) throw new Error(`No se pudo contar ${ruta.split("?")[0]}`);
  return Number(total);
}

/** Números reales de la base para la portada. Si falla, la portada se muestra sin ellos. */
export async function leerEstadisticas(): Promise<Estadisticas | null> {
  "use cache";
  cacheLife("hours");
  cacheTag("estadisticas");
  try {
    const [jugadores, clubes, ediciones, titulos] = await Promise.all([
      contar("jugadores?select=qid"),
      contar("clubes_ligas?select=club_qid"),
      contar("ediciones?select=qid&campeon_qid=not.is.null"),
      contar("titulos_jugador?select=id"),
    ]);
    return { jugadores, clubes, ediciones, titulos };
  } catch {
    return null;
  }
}
