import Image from "next/image";

export type FotoInfo = {
  url: string;
  autor?: string | null;
  licencia?: string | null;
  licencia_url?: string | null;
};

function iniciales(nombre: string) {
  const partes = nombre.split(" ").filter(Boolean);
  return ((partes[0]?.[0] ?? "") + (partes.length > 1 ? partes[partes.length - 1][0] : "")).toUpperCase();
}

/** Foto redonda del jugador, o sus iniciales si no hay foto con licencia libre. */
export function Avatar({
  nombre,
  foto,
  tamano = 40,
  className = "",
}: {
  nombre: string;
  foto?: FotoInfo | null;
  tamano?: number;
  className?: string;
}) {
  const estilo = { width: tamano, height: tamano };
  if (!foto) {
    return (
      <span
        style={{ ...estilo, fontSize: tamano * 0.38 }}
        className={`inline-flex shrink-0 items-center justify-center rounded-full bg-superficie-2 font-display font-bold text-tenue ring-1 ring-borde ${className}`}
        aria-hidden="true"
      >
        {iniciales(nombre)}
      </span>
    );
  }
  return (
    <Image
      src={foto.url}
      alt={`Foto de ${nombre}`}
      width={tamano}
      height={tamano}
      unoptimized
      title={`Foto: ${foto.autor ?? "autor desconocido"}${foto.licencia ? ` · ${foto.licencia}` : ""} (Wikimedia Commons)`}
      style={estilo}
      className={`shrink-0 rounded-full bg-superficie-2 object-cover object-top ring-1 ring-borde ${className}`}
    />
  );
}

/** Créditos de las fotos que se ven en pantalla (lo exige su licencia). */
export function CreditosFotos({ fotos }: { fotos: { nombre: string; foto?: FotoInfo | null }[] }) {
  const conFoto = fotos.filter((f) => f.foto);
  if (conFoto.length === 0) return null;
  return (
    <details className="text-xs text-tenue">
      <summary className="cursor-pointer select-none hover:text-tinta">Créditos de las fotos</summary>
      <ul className="mt-1.5 space-y-0.5">
        {conFoto.map(({ nombre, foto }) => (
          <li key={nombre}>
            {nombre}: {foto!.autor ?? "autor desconocido"}
            {foto!.licencia && (
              <>
                {" · "}
                {foto!.licencia_url ? (
                  <a href={foto!.licencia_url} className="underline hover:text-tinta" target="_blank" rel="noreferrer">
                    {foto!.licencia}
                  </a>
                ) : (
                  foto!.licencia
                )}
              </>
            )}{" "}
            · Wikimedia Commons
          </li>
        ))}
      </ul>
    </details>
  );
}
