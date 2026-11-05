/** minúsculas, sin tildes ni signos: "Ronaldo Nazário" -> "ronaldo nazario" (igual que en el pipeline). */
export function normalizar(texto: string): string {
  return texto
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9 ]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

const SOBRANTES = [
  /\bAssociation Football Club\b/g, /\bFootball Club\b/g, /\bClub de Fútbol\b/g, /\bFútbol Club\b/g,
  /\bFutebol Clube\b/g, /\bFutbol Club\b/g, /\bSociedad Anónima Deportiva\b/g,
  /^Club Atlético\s+/, /^Club Deportivo\s+/, /^Club\s+/,
  /^Società Sportiva Calcio\s+/, /^Società Sportiva\s+/, /^Unione Calcio\s+/, /^Associazione Calcio\s+/,
  /\s+Calcio(\s+\d{4})?$/, /\s+\d{4}$/,
  /\s+A\.\s?F\.\s?C\.$/, /\s+F\.\s?C\.$/, /^F\.\s?C\.\s+/, /^A\.\s?C\.\s+(?=\w{4,})/,
];

/** "Manchester City Football Club" -> "Manchester City" (igual que en el pipeline). */
export function clubCorto(nombre: string): string {
  let corto = nombre;
  for (const patron of SOBRANTES) corto = corto.replace(patron, "");
  corto = corto.replace(/\s{2,}/g, " ").replace(/^[\s,&-]+|[\s,&-]+$/g, "").replace(/\s+(Cricket|and|y)$/, "");
  return corto.length >= 3 ? corto : nombre;
}
