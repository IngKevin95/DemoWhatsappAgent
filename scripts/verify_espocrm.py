"""Self-check contra la API de EspoCRM: crea un Lead y un Case, confirma que se pueden releer.
Requiere ESPOCRM_URL y ESPOCRM_API_KEY configurados (ver .env)."""
import uuid

from agent.integrations import espocrm


def demo():
    sufijo = uuid.uuid4().int % 10**7
    telefono = f"57300{sufijo:07d}"

    lead = espocrm.crear_lead(f"Cliente Demo {sufijo}", telefono, f"Empresa Demo {sufijo}", f"demo{sufijo}@example.com", "Facturación")
    assert lead.get("id"), f"crear_lead no devolvió id: {lead}"
    releido = espocrm.consultar_lead(telefono)
    assert releido and releido["id"] == lead["id"], "consultar_lead no encontró el lead recién creado"
    print(f"Lead OK: {lead['id']}")

    caso = espocrm.crear_caso(telefono, "Caso de prueba de verificación", "Facturación")
    assert caso.get("id"), f"crear_caso no devolvió id: {caso}"
    releido_caso = espocrm.consultar_caso(caso["id"])
    assert releido_caso.get("id") == caso["id"], "consultar_caso no encontró el caso recién creado"
    print(f"Case OK: {caso['id']}")

    print("Self-check OK: Lead y Case creados y releídos correctamente.")


if __name__ == "__main__":
    demo()
