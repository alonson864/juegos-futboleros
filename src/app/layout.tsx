import type { Metadata, Viewport } from "next";
import { Barlow_Condensed, Inter } from "next/font/google";
import Link from "next/link";
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
  description: "Juegos de fútbol para jugar con tus amigos.",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#0e7a3e" },
    { media: "(prefers-color-scheme: dark)", color: "#0b1510" },
  ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="es"
      className={`${inter.variable} ${barlowCondensed.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col">
        <header className="bg-cancha text-sobre-cancha">
          <div className="mx-auto flex h-14 w-full max-w-3xl items-center px-4 lg:h-16 lg:max-w-6xl lg:px-8">
            <Link href="/" className="flex items-center gap-2" aria-label="Juegos Futboleros, inicio">
              <Pelota />
              <span className="font-display text-xl font-extrabold uppercase tracking-wide lg:text-2xl">
                Juegos Futboleros
              </span>
            </Link>
          </div>
        </header>
        {children}
        <footer className="mt-auto border-t border-borde">
          <div className="mx-auto flex max-w-3xl flex-col gap-1 px-4 py-5 text-center text-xs text-tenue lg:max-w-6xl lg:text-sm">
            <p>Hecho para jugar con amigos ⚽</p>
            <p>
              Datos de{" "}
              <a href="https://www.wikidata.org" className="underline hover:text-tinta">Wikidata</a> (CC0) y{" "}
              <a href="https://en.wikipedia.org" className="underline hover:text-tinta">Wikipedia</a>, con licencia{" "}
              <a href="https://creativecommons.org/licenses/by-sa/4.0/deed.es" className="underline hover:text-tinta">
                CC BY-SA 4.0
              </a>
              .
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}

function Pelota() {
  return (
    <svg viewBox="0 0 24 24" className="h-7 w-7" aria-hidden="true">
      <circle cx="12" cy="12" r="10.5" fill="currentColor" />
      <path
        d="M12 7.2l3.6 2.6-1.4 4.2H9.8L8.4 9.8z"
        className="fill-cancha"
      />
      <path
        d="M12 1.5v5.7M15.6 9.8l5.6-1.8M14.2 14l3.4 4.6M9.8 14l-3.4 4.6M8.4 9.8L2.8 8"
        stroke="var(--cancha)"
        strokeWidth="1.4"
        fill="none"
      />
    </svg>
  );
}
