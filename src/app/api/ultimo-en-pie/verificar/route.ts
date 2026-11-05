import { leerDeSupabase } from "@/lib/supabase";
import { clubCorto } from "@/lib/texto";

type Parametros =
  | { tipo: "club"; clubes: string[] }
  | { tipo: "clubes"; clubes: string[][] }
  | { tipo: "seleccion"; equipos: string[]; pais: string }
  | { tipo: "titulo"; familia: string; competiciones: string[]; individual: boolean }
  | { tipo: "nacion_club"; clubes: string[]; paises: string[] }
  | { tipo: "muchos_clubes"; minimo: number }
  | { tipo: "torneo_con"; competiciones: string[]; equipos: string[]; pais: string; torneo: string };

type Evidencia = { texto: string; detalle?: string; destacado: boolean };

/** Filiales y reservas (Barcelona C, Real Madrid Castilla, Bayern II…): no cuentan como otro club. */
const FILIAL = /(\s"?[BC]"?|\sII|\sReserves?|\sAcademy|\sCastilla|\sAtl[eè]tic|\sUnder-\d+|\sU\d+)$/i;

const lista = (qids: string[]) => `(${qids.map((q) => `"${q}"`).join(",")})`;
const anio = (f: string | null) => (f ? f.slice(0, 4) : null);
const periodo = (desde: string | number | null, hasta: string | number | null) =>
  desde ? `${desde}–${hasta ?? "hoy"}` : undefined;

/**
 * ¿Cumple el jugador la categoría?  /api/ultimo-en-pie/verificar?categoria=12&jugador=Q615
 * cumple: true / false / null (null = no tenemos datos suficientes para afirmarlo)
 */
export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  const categoria = Number(params.get("categoria"));
  const jugador = params.get("jugador") ?? "";
  if (!Number.isInteger(categoria) || !/^Q\d+$/.test(jugador)) {
    return Response.json({ error: "Parámetros inválidos." }, { status: 400 });
  }

  try {
    const [cat] = await leerDeSupabase<{ titulo: string; parametros: Parametros }[]>(
      `ultimo_en_pie_categorias?id=eq.${categoria}&select=titulo,parametros`,
    );
    const [j] = await leerDeSupabase<{ nombre: string; nacionalidades: string[] }[]>(
      `jugadores_final?qid=eq.${jugador}&select=nombre,nacionalidades`,
    );
    if (!cat || !j) return Response.json({ error: "No encontrado." }, { status: 404 });
    const p = cat.parametros;

    if (p.tipo === "titulo") {
      const [titulos, leido] = await Promise.all([
        leerDeSupabase<{ anio: number | null; temporada: string | null; individual: boolean }[]>(
          `titulos_jugador_final?jugador_qid=eq.${jugador}&competicion_qid=in.${lista(p.competiciones)}` +
            `&select=anio,temporada,individual&order=anio.asc`,
        ),
        leerDeSupabase<unknown[]>(`jugadores_wikipedia?jugador_qid=eq.${jugador}&select=jugador_qid`),
      ]);
      const validos = titulos.filter((t) => p.individual || !t.individual);
      const evidencia: Evidencia[] = validos.map((t) => ({ texto: t.temporada ?? String(t.anio), destacado: true }));
      if (validos.length > 0) {
        return Response.json({ cumple: true, nombre: j.nombre, detalle: `Lo ganó: ${evidencia.map((e) => e.texto).join(", ")}.`, evidencia });
      }
      return Response.json(
        leido.length > 0
          ? { cumple: false, nombre: j.nombre, detalle: "Según su palmarés en Wikipedia, nunca lo ganó.", evidencia }
          : {
              cumple: null,
              nombre: j.nombre,
              detalle: "No tenemos su palmarés completo, así que no podemos verificarlo. Decidan entre ustedes.",
              evidencia,
            },
      );
    }

    // Clubes y selecciones: pasos de Wikidata + carrera de Wikipedia
    const [pasos, carrera] = await Promise.all([
      leerDeSupabase<{ club_qid: string; inicio: string | null; fin: string | null }[]>(
        `pasos_por_club_final?jugador_qid=eq.${jugador}&select=club_qid,inicio,fin&order=inicio.asc.nullslast`,
      ),
      leerDeSupabase<{ equipo_qid: string | null; equipo_texto: string; desde: number | null; hasta: number | null }[]>(
        `carrera_wikipedia?jugador_qid=eq.${jugador}&select=equipo_qid,equipo_texto,desde,hasta&order=seleccion.asc,orden.asc`,
      ),
    ]);
    const qids = [...new Set([...pasos.map((x) => x.club_qid), ...carrera.flatMap((x) => (x.equipo_qid ? [x.equipo_qid] : []))])];
    const [alias, clubes] = qids.length
      ? await Promise.all([
          leerDeSupabase<{ qid: string; club_qid: string }[]>(
            `clubes_alias?or=(qid.in.${lista(qids)},club_qid.in.${lista(qids)})&select=qid,club_qid`,
          ),
          leerDeSupabase<{ qid: string; nombre: string; tipo: string }[]>(
            `clubes_final?qid=in.${lista(qids)}&select=qid,nombre,tipo`,
          ),
        ])
      : [[], []];
    const equipos = new Set(qids);
    for (const a of alias) {
      if (equipos.has(a.qid) || equipos.has(a.club_qid)) {
        equipos.add(a.qid);
        equipos.add(a.club_qid);
      }
    }
    const tipo = new Map(clubes.map((c) => [c.qid, c.tipo]));
    const nombre = new Map(clubes.map((c) => [c.qid, c.nombre]));

    const leido = async () =>
      (await leerDeSupabase<unknown[]>(`jugadores_wikipedia?jugador_qid=eq.${jugador}&select=jugador_qid`)).length > 0;

    // Clubes distintos del jugador (sin juveniles ni filiales; fichas equivalentes cuentan como una)
    const canonico = (q: string) => {
      const grupo = [q, ...alias.filter((a) => a.qid === q || a.club_qid === q).flatMap((a) => [a.qid, a.club_qid])];
      return grupo.sort()[0];
    };
    const clubesDistintos = new Map<string, Evidencia>();
    for (const x of pasos) {
      if (tipo.get(x.club_qid) !== "club" || FILIAL.test(nombre.get(x.club_qid) ?? "")) continue;
      const k = canonico(x.club_qid);
      if (!clubesDistintos.has(k))
        clubesDistintos.set(k, { texto: clubCorto(nombre.get(x.club_qid) ?? x.club_qid), detalle: periodo(anio(x.inicio), anio(x.fin)), destacado: false });
    }
    for (const x of carrera) {
      if (!x.equipo_qid || tipo.get(x.equipo_qid) !== "club" || FILIAL.test(x.equipo_texto)) continue;
      const k = canonico(x.equipo_qid);
      if (!clubesDistintos.has(k)) clubesDistintos.set(k, { texto: x.equipo_texto, detalle: periodo(x.desde, x.hasta), destacado: false });
    }

    if (p.tipo === "muchos_clubes") {
      const evidencia = [...clubesDistintos.values()].map((e) => ({ ...e, destacado: true }));
      const n = evidencia.length;
      if (n >= p.minimo) {
        return Response.json({ cumple: true, nombre: j.nombre, detalle: `Jugó en ${n} clubes.`, evidencia });
      }
      // Solo con la carrera completa de Wikipedia podemos afirmar que fueron menos
      return Response.json(
        (await leido())
          ? { cumple: false, nombre: j.nombre, detalle: `Jugó en ${n} clubes según Wikipedia: no llega.`, evidencia }
          : { cumple: null, nombre: j.nombre, detalle: `En nuestros registros tiene ${n} clubes, pero puede faltar alguno. Decidan entre ustedes.`, evidencia },
      );
    }

    if (p.tipo === "nacion_club") {
      const nacionalidad = (j.nacionalidades ?? []).some((n) => p.paises.includes(n));
      const enClub = p.clubes.some((q) => equipos.has(q));
      const pedidos = new Set(p.clubes.map(canonico));
      const evidencia = [...clubesDistintos.entries()].map(([k, e]) => ({ ...e, destacado: pedidos.has(k) }));
      if (nacionalidad && enClub) return Response.json({ cumple: true, nombre: j.nombre, detalle: "Sí cumple.", evidencia });
      if ((j.nacionalidades ?? []).length === 0)
        return Response.json({ cumple: null, nombre: j.nombre, detalle: "No tenemos su nacionalidad registrada. Decidan entre ustedes.", evidencia });
      return Response.json({
        cumple: false,
        nombre: j.nombre,
        detalle: !nacionalidad
          ? "No cumple: no es de ese origen según sus registros."
          : "No cumple: no aparece ese club en sus registros.",
        evidencia,
      });
    }

    if (p.tipo === "torneo_con") {
      const participaciones = await leerDeSupabase<{ anio: number | null }[]>(
        `participaciones?jugador_qid=eq.${jugador}&competicion_qid=in.${lista(p.competiciones)}&select=anio&order=anio.asc`,
      );
      const selecciones = [...equipos].filter((q) => tipo.get(q) === "seleccion");
      const conEsa = p.equipos.some((q) => equipos.has(q));
      const otras = selecciones.filter((q) => !p.equipos.includes(q));
      const evidencia: Evidencia[] = [
        ...participaciones.map((x) => ({ texto: `${p.torneo === "un Mundial" ? "Mundial" : "Torneo"} ${x.anio ?? ""}`.trim(), destacado: true })),
        ...selecciones.map((q) => ({ texto: nombre.get(q) ?? q, destacado: p.equipos.includes(q) })),
      ];
      if (participaciones.length > 0 && conEsa && otras.length === 0)
        return Response.json({ cumple: true, nombre: j.nombre, detalle: "Sí cumple.", evidencia });
      if (!conEsa && selecciones.length > 0)
        return Response.json({ cumple: false, nombre: j.nombre, detalle: "No cumple: nunca jugó por esa selección.", evidencia });
      if (conEsa && participaciones.length > 0 && otras.length > 0)
        return Response.json({ cumple: null, nombre: j.nombre, detalle: "Jugó Mundiales y por varias selecciones: no sabemos con cuál fue. Decidan entre ustedes.", evidencia });
      return Response.json({
        cumple: null,
        nombre: j.nombre,
        detalle: "No figura en nuestros registros de Mundiales con esa selección, pero puede faltar el dato. Decidan entre ustedes.",
        evidencia,
      });
    }

    const requeridos: string[][] =
      p.tipo === "club" ? [p.clubes] : p.tipo === "clubes" ? p.clubes : [p.equipos];
    const cumple = requeridos.every((grupo) => grupo.some((q) => equipos.has(q)));
    const todosRequeridos = new Set(requeridos.flat());
    const quiere = p.tipo === "seleccion" ? "seleccion" : "club";

    // Evidencia: cada paso por un equipo del tipo que importa, sin repetir
    const vistos = new Set<string>();
    const evidencia: Evidencia[] = [];
    for (const x of pasos) {
      if (tipo.get(x.club_qid) !== quiere || vistos.has(x.club_qid)) continue;
      vistos.add(x.club_qid);
      evidencia.push({
        texto: quiere === "club" ? clubCorto(nombre.get(x.club_qid) ?? x.club_qid) : (nombre.get(x.club_qid) ?? x.club_qid),
        detalle: periodo(anio(x.inicio), anio(x.fin)),
        destacado: todosRequeridos.has(x.club_qid),
      });
    }
    for (const x of carrera) {
      if (!x.equipo_qid || vistos.has(x.equipo_qid) || tipo.get(x.equipo_qid) !== quiere) continue;
      vistos.add(x.equipo_qid);
      evidencia.push({ texto: x.equipo_texto, detalle: periodo(x.desde, x.hasta), destacado: todosRequeridos.has(x.equipo_qid) });
    }

    if (cumple) {
      return Response.json({ cumple: true, nombre: j.nombre, detalle: "Sí cumple.", evidencia });
    }
    const sinDatos = evidencia.length === 0;
    return Response.json({
      cumple: sinDatos ? null : false,
      nombre: j.nombre,
      detalle: sinDatos
        ? `No tenemos registro de sus ${quiere === "club" ? "clubes" : "selecciones"}, así que no podemos verificarlo. Decidan entre ustedes.`
        : "No cumple: no aparece en sus registros.",
      evidencia,
    });
  } catch {
    return Response.json({ error: "No se pudo verificar en este momento." }, { status: 502 });
  }
}
