/**
 * Lectura de datos desde Supabase usando su API web (PostgREST) con la clave
 * publishable, que solo permite leer. Corre en el servidor.
 */
export async function leerDeSupabase<T>(ruta: string): Promise<T> {
  const url = process.env.SUPABASE_URL;
  const clave = process.env.SUPABASE_PUBLISHABLE_KEY;
  if (!url || !clave) {
    throw new Error("Faltan SUPABASE_URL o SUPABASE_PUBLISHABLE_KEY en las variables de entorno.");
  }
  const respuesta = await fetch(`${url}/rest/v1/${ruta}`, {
    headers: { apikey: clave, Accept: "application/json" },
  });
  if (!respuesta.ok) {
    throw new Error(`Supabase respondió ${respuesta.status} al leer ${ruta.split("?")[0]}`);
  }
  return (await respuesta.json()) as T;
}
