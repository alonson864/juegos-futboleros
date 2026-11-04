"""Aplica en orden los archivos de pipeline/migraciones/ que todavía no se aplicaron.

Se puede correr muchas veces: cada migración queda registrada y no se repite.
Uso: pipeline/.venv/bin/python pipeline/migrar.py
"""

from pathlib import Path

from db import conectar

CARPETA = Path(__file__).resolve().parent / "migraciones"


def main() -> None:
    archivos = sorted(CARPETA.glob("*.sql"))
    with conectar() as conn:
        conn.execute(
            """
            create table if not exists migraciones_aplicadas (
              nombre      text primary key,
              aplicada_en timestamptz not null default now()
            )
            """
        )
        conn.execute("alter table migraciones_aplicadas enable row level security")
        conn.commit()

        hechas = {fila[0] for fila in conn.execute("select nombre from migraciones_aplicadas")}
        pendientes = [a for a in archivos if a.name not in hechas]
        if not pendientes:
            print("La base ya está al día. No hay migraciones pendientes.")
            return

        for archivo in pendientes:
            print(f"Aplicando {archivo.name}…")
            # Todo el archivo en una transacción: o se aplica completo o nada.
            with conn.transaction():
                conn.execute(archivo.read_text(encoding="utf-8"))
                conn.execute(
                    "insert into migraciones_aplicadas (nombre) values (%s)", (archivo.name,)
                )
            print(f"  ✓ {archivo.name}")

    print(f"Listo: {len(pendientes)} migración(es) aplicada(s).")


if __name__ == "__main__":
    main()
