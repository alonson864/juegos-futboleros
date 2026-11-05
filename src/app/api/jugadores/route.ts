import { leerDeSupabase } from "@/lib/supabase";
import { normalizar } from "@/lib/texto";

type Fila = { qid: string; nombre: string; popularidad: number };

/** Sugerencias de jugadores mientras se escribe: /api/jugadores?q=ronaldo */
export async function GET(request: Request) {
  const q = normalizar(new URL(request.url).searchParams.get("q") ?? "");
  const palabras = q.split(" ").filter((p) => p.length >= 2).slice(0, 4);
  if (palabras.length === 0) return Response.json([]);

  const filtro = (union: "and" | "or") =>
    `${union}=(${palabras.map((p) => `busqueda.ilike.*${p}*`).join(",")})`;
  const consulta = (union: "and" | "or") =>
    leerDeSupabase<Fila[]>(
      `jugadores?select=qid,nombre,popularidad&${filtro(union)}&order=popularidad.desc&limit=8`,
    );

  try {
    // 1) la frase exacta ("di maria"), 2) todas las palabras, 3) alguna palabra
    const frase = palabras.join(" ");
    const exactas =
      palabras.length > 1
        ? await leerDeSupabase<Fila[]>(
            `jugadores?select=qid,nombre,popularidad&busqueda=ilike.*${encodeURIComponent(frase)}*&order=popularidad.desc&limit=8`,
          )
        : [];
    let filas = [...exactas];
    if (filas.length < 8) {
      const todas = await consulta("and");
      filas = [...filas, ...todas.filter((x) => !filas.some((y) => y.qid === x.qid))];
    }
    if (filas.length === 0 && palabras.length > 1) filas = await consulta("or");
    return Response.json(filas.slice(0, 8));
  } catch {
    return Response.json({ error: "No se pudo buscar en este momento." }, { status: 502 });
  }
}
