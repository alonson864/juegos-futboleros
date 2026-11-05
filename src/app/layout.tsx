import type { Metadata, Viewport } from "next";
import { Barlow_Condensed, Inter } from "next/font/google";
import Link from "next/link";
import { Pelota } from "./componentes/Cancha";
import Navegacion from "./componentes/Navegacion";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const barlowCondensed = Barlow_Condensed({
  variable: "--font-barlow-condensed",
  subsets: ["latin"],
  weight: ["600", "700", "800"],
});

export const metadata: Metadata = {
  title: "Juegos Futboleros",
  description: "Juegos de fútbol para jugar con tus amigos, con datos reales de jugadores, clubes y torneos.",
};

export const viewport: Viewport = {
  themeColor: "#07261a",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="es"
      className={`${inter.variable} ${barlowCondensed.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col">
        <header className="sticky top-0 z-30 border-b border-white/10 bg-noche/90 text-white backdrop-blur-md">
          <div className="mx-auto flex h-14 w-full max-w-3xl items-center justify-between gap-4 px-4 lg:h-16 lg:max-w-6xl lg:px-8">
            <Link href="/" className="flex items-center gap-2.5" aria-label="Juegos Futboleros, inicio">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-cancha text-white shadow-[0_0_0_1px_rgba(255,255,255,0.15)_inset] lg:h-9 lg:w-9">
                <Pelota className="h-5 w-5 lg:h-6 lg:w-6" />
              </span>
              <span className="font-display text-lg leading-none font-extrabold uppercase tracking-wide lg:text-2xl">
                Juegos <span className="text-tarjeta">Futboleros</span>
              </span>
            </Link>
            <Navegacion />
          </div>
        </header>

        {children}

        <footer className="mt-auto bg-noche text-white/70">
          <div className="mx-auto grid w-full max-w-3xl gap-8 px-4 py-10 text-sm sm:grid-cols-3 lg:max-w-6xl lg:px-8 lg:py-14">
            <div>
              <p className="flex items-center gap-2 font-display text-xl font-extrabold uppercase text-white">
                <Pelota className="h-5 w-5" /> Juegos Futboleros
              </p>
              <p className="mt-3 max-w-xs">
                Juegos de fútbol para jugar con amigos, armados con datos reales de jugadores, clubes y torneos.
              </p>
            </div>
            <div>
              <p className="font-display text-base font-bold uppercase tracking-wide text-white">Juegos</p>
              <ul className="mt-3 space-y-2">
                <li>
                  <Link href="/juegos/conexiones" className="hover:text-white">
                    Conexiones
                  </Link>
                </li>
                <li>
                  <Link href="/juegos/dato-falso" className="hover:text-white">
                    Dato Falso Futbolero
                  </Link>
                </li>
                <li>
                  <Link href="/juegos/ultimo-en-pie" className="hover:text-white">
                    Último en pie
                  </Link>
                </li>
                <li className="text-white/40">Mayor o menor (pronto)</li>
              </ul>
            </div>
            <div>
              <p className="font-display text-base font-bold uppercase tracking-wide text-white">Fuentes</p>
              <p className="mt-3">
                Datos de{" "}
                <a href="https://www.wikidata.org" className="underline decoration-white/30 hover:text-white">
                  Wikidata
                </a>{" "}
                (CC0) y{" "}
                <a href="https://en.wikipedia.org" className="underline decoration-white/30 hover:text-white">
                  Wikipedia
                </a>
                , con licencia{" "}
                <a
                  href="https://creativecommons.org/licenses/by-sa/4.0/deed.es"
                  className="underline decoration-white/30 hover:text-white"
                >
                  CC BY-SA 4.0
                </a>
                . Fotos de Wikimedia Commons con su autor y licencia.
              </p>
            </div>
          </div>
          <div className="border-t border-white/10">
            <p className="mx-auto max-w-3xl px-4 py-4 text-xs text-white/40 lg:max-w-6xl lg:px-8">
              Hecho para jugar con amigos ⚽
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
