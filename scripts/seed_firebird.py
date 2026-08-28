"""Crea tabla LICENCIAS (si falta) y siembra 3 escenarios de demo. Idempotente."""
import os

import firebird.driver as fb

HOST = os.getenv("FIREBIRD_HOST", "localhost")
DSN = f"{HOST}/3050:licencias.fdb"
USER = "sysdba"
PASSWORD = os.getenv("ISC_PASSWORD", "demobot")

# Identificaciones fijas y documentadas para la demo:
# 900111222 = con licencia y contrato de soporte activo
# 900333444 = con licencia pero sin contrato de soporte
# 900555666 = no tiene ninguna licencia (no se siembra fila)
LICENCIAS = [
    (1, "900111222", "Facturación", "2024-01-15", True, "2026-12-31"),
    (2, "900333444", "Inventario", "2024-03-10", False, None),
]


def _connect():
    return fb.connect(database=DSN, user=USER, password=PASSWORD)


def _crear_tabla(con):
    cur = con.cursor()
    cur.execute("SELECT 1 FROM RDB$RELATIONS WHERE RDB$RELATION_NAME = 'LICENCIAS'")
    if cur.fetchone():
        return
    cur.execute(
        """
        CREATE TABLE LICENCIAS (
          ID INTEGER NOT NULL PRIMARY KEY,
          IDENTIFICACION VARCHAR(20) NOT NULL,
          MODULO VARCHAR(50) NOT NULL,
          FECHA_VENTA DATE NOT NULL,
          SOPORTE_ACTIVO BOOLEAN NOT NULL,
          SOPORTE_HASTA DATE
        )
        """
    )
    con.commit()


def _sembrar(con):
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM LICENCIAS")
    if cur.fetchone()[0] > 0:
        print("Tabla LICENCIAS ya tiene datos, no se siembra.")
        return
    cur.executemany(
        "INSERT INTO LICENCIAS (ID, IDENTIFICACION, MODULO, FECHA_VENTA, SOPORTE_ACTIVO, SOPORTE_HASTA) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        LICENCIAS,
    )
    con.commit()
    print(f"Sembradas {len(LICENCIAS)} licencias.")


def consultar(con, identificacion: str) -> str:
    cur = con.cursor()
    cur.execute("SELECT SOPORTE_ACTIVO FROM LICENCIAS WHERE IDENTIFICACION = ?", (identificacion,))
    fila = cur.fetchone()
    if not fila:
        return "sin_licencia"
    return "con_licencia_con_soporte" if fila[0] else "con_licencia_sin_soporte"


def demo():
    con = _connect()
    try:
        assert consultar(con, "900111222") == "con_licencia_con_soporte"
        assert consultar(con, "900333444") == "con_licencia_sin_soporte"
        assert consultar(con, "900555666") == "sin_licencia"
        print("Self-check OK: 3 escenarios validados.")
    finally:
        con.close()


if __name__ == "__main__":
    con = _connect()
    try:
        _crear_tabla(con)
        _sembrar(con)
    finally:
        con.close()
    demo()
