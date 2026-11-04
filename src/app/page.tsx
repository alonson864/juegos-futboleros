type Juego = {
  titulo: string;
  descripcion: string;
  emoji: string;
};

const juegos: Juego[] = [
  {
    titulo: "Conexiones",
    descripcion:
      "Agrupa jugadores, clubes y selecciones en cuatro grupos según lo que tienen en común.",
    emoji: "🔗",
  },
  {
    titulo: "Mayor o menor",
    descripcion:
      "¿Más goles, más partidos, más títulos? Adivina si el siguiente dato es mayor o menor.",
    emoji: "⬆️",
  },
];

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center px-6 py-16">
      <header className="mb-12 text-center">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          ⚽ Juegos Futboleros
        </h1>
        <p className="mt-4 text-lg text-foreground/70">
          Juegos de fútbol para retar a tus amigos.
        </p>
      </header>

      <section className="grid w-full max-w-3xl gap-6 sm:grid-cols-2">
        {juegos.map((juego) => (
          <article
            key={juego.titulo}
            className="flex flex-col rounded-2xl border border-foreground/10 bg-foreground/[0.03] p-6 shadow-sm"
          >
            <span className="text-4xl" aria-hidden="true">
              {juego.emoji}
            </span>
            <h2 className="mt-4 text-2xl font-semibold">{juego.titulo}</h2>
            <p className="mt-2 flex-1 text-foreground/70">{juego.descripcion}</p>
            <span className="mt-6 inline-flex w-fit items-center rounded-full bg-emerald-600/15 px-3 py-1 text-sm font-medium text-emerald-700 dark:text-emerald-400">
              Próximamente
            </span>
          </article>
        ))}
      </section>
    </main>
  );
}
