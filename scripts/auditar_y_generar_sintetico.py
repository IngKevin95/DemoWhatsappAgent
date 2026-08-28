"""Auditoría de base de conocimiento y generación de datos sintéticos.
Este script analiza la estructura de los archivos Markdown en la carpeta `knowledge/`,
detecta problemas de coincidencia literal para `buscar_en_knowledge` y genera un
dataset de consultas sintéticas (QA) clasificadas por intención para pruebas y RAG.
"""

import json
import os
import re
from collections import defaultdict
from pathlib import Path

# Directorio del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
OUTPUT_DATASET = KNOWLEDGE_DIR / "synthetic_data.json"
ARTIFACT_DIR = Path(r"C:\Users\kevin\.gemini\antigravity-cli\brain\d08c1ae0-c494-44b9-97c0-9af64ae51b3d")

def auditar_knowledge():
    files = sorted(KNOWLEDGE_DIR.glob("*.md"))
    
    h1_headers = []
    h2_headers = defaultdict(list)
    
    for f in files:
        content = f.read_text(encoding="utf-8")
        lines = content.splitlines()
        
        for idx, line in enumerate(lines, 1):
            # Detectar H1
            h1_match = re.match(r"^#\s+(.+)$", line)
            if h1_match:
                h1_headers.append({
                    "file": f.name,
                    "line": idx,
                    "title": h1_match.group(1).strip()
                })
                
            # Detectar H2
            h2_match = re.match(r"^##\s+(.+)$", line)
            if h2_match:
                h2_headers[h2_match.group(1).strip()].append({
                    "file": f.name,
                    "line": idx
                })
                
    # Hallar duplicados
    h2_duplicates = {h: instances for h, instances in h2_headers.items() if len(instances) > 1}
    
    return h1_headers, h2_duplicates, files

def generar_datos_sinteticos():
    # Definición manual de datos sintéticos basados en la base de conocimientos real
    dataset = [
        # --- COMERCIAL & PRECIOS ---
        {
            "query": "¿Cuánto cuesta la licencia del módulo de Nómina?",
            "intent": "comercial",
            "file": "democorp_modulos.md",
            "section": "Nómina",
            "expected_entities": {"modulo": "Nómina"},
            "ground_truth": "Liquidación de nómina electrónica, seguridad social, prestaciones sociales, préstamos y descuentos, certificados laborales."
        },
        {
            "query": "precio modulo contabilidad anual",
            "intent": "comercial",
            "file": "democorp_modulos.md",
            "section": "Contabilidad",
            "expected_entities": {"modulo": "Contabilidad"},
            "ground_truth": "Plan de cuentas configurable, causación automática desde todos los módulos, estados financieros NIIF, centros de costo, cierre de períodos."
        },
        {
            "query": "Hola, me interesa saber los precios de los combos de facturación e inventario",
            "intent": "comercial",
            "file": "comercial.md",
            "section": "Productos relacionados",
            "expected_entities": {"tema": "combos"},
            "ground_truth": "ERP DemoCorp, CRM, Facturación Electrónica, Inventarios, Contabilidad..."
        },
        {
            "query": "¿Qué módulos incluye el Combo Emprendedor?",
            "intent": "comercial",
            "file": "comercial.md",
            "section": "Preguntas frecuentes",
            "expected_entities": {"combo": "Combo Emprendedor"},
            "ground_truth": "El ERP está compuesto por módulos independientes que pueden implementarse según las necesidades..."
        },
        {
            "query": "Tienen algun paquete economico para punto de venta pos?",
            "intent": "comercial",
            "file": "democorp_modulos.md",
            "section": "POS",
            "expected_entities": {"modulo": "POS"},
            "ground_truth": "Punto de venta táctil, múltiples medios de pago, turnos de caja, facturación electrónica en línea, integración con inventario en tiempo real."
        },
        
        # --- SOPORTE & ERRORES ---
        {
            "query": "Tengo un error de factura rechazada por la DIAN, no genera el codigo CUFE",
            "intent": "soporte",
            "file": "errores_fallas_comunes_demo.md",
            "section": "Error: factura electrónica rechazada por DIAN",
            "expected_entities": {"error": "factura rechazada DIAN"},
            "ground_truth": "Causas frecuentes: Datos fiscales del cliente incompletos. Resolución DIAN vencida o sin numeración disponible. Certificado digital vencido. Impuestos o retenciones mal configurados."
        },
        {
            "query": "Al intentar facturar me sale que el producto no tiene stock, pero si tengo en la bodega física",
            "intent": "soporte",
            "file": "errores_fallas_comunes_demo.md",
            "section": "Error: producto sin stock al facturar",
            "expected_entities": {"error": "sin stock"},
            "ground_truth": "Causas frecuentes: Producto en otra bodega. Entrada de compra no contabilizada. Inventario reservado por pedido. Diferencia entre inventario físico y sistema."
        },
        {
            "query": "No me aparece un pago de cartera en el sistema, la factura sigue vencida",
            "intent": "soporte",
            "file": "errores_fallas_comunes_demo.md",
            "section": "Error: no aparece un pago en cartera",
            "expected_entities": {"error": "pago no aparece cartera"},
            "ground_truth": "Causas frecuentes: Pago registrado en Tesorería pero no aplicado a cartera. Consignación sin identificar. Diferencia en valor pagado. Pago aplicado a otro cliente o factura."
        },
        {
            "query": "Las ventas de mi sede POS no se estan sincronizando al ERP central",
            "intent": "soporte",
            "file": "errores_fallas_comunes_demo.md",
            "section": "Error: POS no sincroniza ventas",
            "expected_entities": {"error": "POS no sincroniza"},
            "ground_truth": "Causas frecuentes: Sin conexión a internet. Turno de caja no cerrado. Servicio de sincronización detenido. Credenciales del POS vencidas."
        },
        {
            "query": "El sistema me rechaza mi contraseña y no puedo entrar al ERP",
            "intent": "soporte",
            "file": "errores_fallas_comunes_demo.md",
            "section": "Error: usuario no puede ingresar",
            "expected_entities": {"error": "usuario no ingresa"},
            "ground_truth": "Causas frecuentes: Contraseña incorrecta. Usuario inactivo. Perfil sin permisos. Bloqueo temporal por intentos fallidos."
        },
        {
            "query": "El balance contable tiene diferencias y no cuadra",
            "intent": "soporte",
            "file": "errores_fallas_comunes_demo.md",
            "section": "Error: reporte contable no cuadra",
            "expected_entities": {"error": "reporte contable no cuadra"},
            "ground_truth": "Causas frecuentes: Documentos sin contabilizar. Periodo contable cerrado parcialmente. Cuentas mal parametrizadas. Terceros o centros de costo incompletos."
        },
        {
            "query": "El sistema DemoCorp esta demasiado lento hoy en todas las pantallas",
            "intent": "soporte",
            "file": "errores_fallas_comunes_demo.md",
            "section": "Falla común: lentitud general del sistema",
            "expected_entities": {"error": "lentitud general"},
            "ground_truth": "Causas frecuentes: Filtros de fecha muy amplios. Muchos usuarios generando reportes pesados. Conexión inestable. Navegador con caché saturada."
        },

        # --- PREVENTA & IMPLEMENTACIÓN & AGENDAS ---
        {
            "query": "¿Cuánto tiempo toma implementar el ERP completo?",
            "intent": "comercial",
            "file": "preventa.md",
            "section": "Preguntas frecuentes",
            "expected_entities": {"tema": "tiempo de implementación"},
            "ground_truth": "¿Cuánto tiempo toma la implementación?"
        },
        {
            "query": "Quiero saber que datos o informacion necesito darles para la implementacion",
            "intent": "comercial",
            "file": "implementacion.md",
            "section": "Información requerida",
            "expected_entities": {"tema": "información requerida"},
            "ground_truth": "Empresa. Proyecto. Responsable. Módulos."
        },
        {
            "query": "¿Cómo puedo renovar mi licencia anual de DemoCorp?",
            "intent": "comercial",
            "file": "licenciamiento.md",
            "section": "Preguntas frecuentes",
            "expected_entities": {"tema": "renovar licencia"},
            "ground_truth": "¿Cómo renovar la licencia?"
        },
        {
            "query": "Quiero programar una cita para una demostración del ERP",
            "intent": "comercial",
            "file": "comercial.md",
            "section": "Servicios ofrecidos",
            "expected_entities": {"accion": "agendar cita"},
            "ground_truth": "Demostraciones del ERP. Presentación de módulos."
        },
        {
            "query": "¿Tienen soporte técnico incluido con la licencia o toca pagarlo aparte?",
            "intent": "comercial",
            "file": "democorp_modulos.md",
            "section": "Precios y Soporte",
            "expected_entities": {"tema": "soporte incluido"},
            "ground_truth": "Todos los valores comerciales y precios de los módulos individuales y combos son anuales e incluyen soporte técnico por un año."
        },

        # --- OTROS ---
        {
            "query": "Hola buenas tardes",
            "intent": "otro",
            "file": None,
            "section": None,
            "expected_entities": {},
            "ground_truth": None
        },
        {
            "query": "gracias por la informacion, chao",
            "intent": "otro",
            "file": None,
            "section": None,
            "expected_entities": {},
            "ground_truth": None
        },
        {
            "query": "¿De qué color es el caballo blanco de Simón Bolívar?",
            "intent": "otro",
            "file": None,
            "section": None,
            "expected_entities": {},
            "ground_truth": None
        }
    ]
    return dataset

def main():
    print("Iniciando auditoría de 'knowledge/'...")
    h1, h2_dups, files = auditar_knowledge()
    
    print(f"Total archivos analizados: {len(files)}")
    print(f"Total H1 (Títulos) encontrados: {len(h1)}")
    print(f"Total H2 duplicados que causan colisiones en buscar_en_knowledge: {len(h2_dups)}")
    
    # Escribir reporte
    report = []
    report.append("# Reporte de Auditoría de Base de Conocimiento (Knowledge Base)")
    report.append(f"**Fecha:** 2026-07-15")
    report.append(f"**Archivos analizados:** {len(files)}")
    report.append("\n## 1. Problemas de Trazabilidad e Indexación (para `buscar_en_knowledge`) \n")
    report.append("> [!IMPORTANT]")
    report.append("> La tool `buscar_en_knowledge` realiza una coincidencia basada en `split('## ')` y un `.startswith()` literal. Los siguientes problemas impiden que el bot acceda correctamente a la información:")
    
    report.append("\n### A. Encabezados H2 Duplicados (Colisiones Críticas)")
    report.append("Dado que el bot une todos los archivos en orden alfabético y busca el primer bloque que coincida con el encabezado, los siguientes H2 duplicados harán que el bot **siempre devuelva el contenido del primer archivo alfabéticamente**, ignorando los demás:")
    
    for h2, instances in sorted(h2_dups.items()):
        inst_str = ", ".join([f"[{inst['file']}](file:///{BASE_DIR.as_posix()}/knowledge/{inst['file']}#L{inst['line']})" for inst in instances])
        report.append(f"- `## {h2}`: Presente en {inst_str}")
        
    report.append("\n### B. Títulos H1 invisibles")
    report.append("El título H1 (`# ...`) de cada documento queda truncado o englobado dentro de un bloque anterior o inexistente debido al `split('## ')`. Los siguientes títulos no pueden ser recuperados directamente por la tool actual:")
    for h1_item in h1:
        report.append(f"- `# {h1_item['title']}` en [{h1_item['file']}](file:///{BASE_DIR.as_posix()}/knowledge/{h1_item['file']}#L{h1_item['line']})")
        
    report.append("\n## 2. Recomendaciones de Depuración")
    report.append("1. **Namespacing de Encabezados:** Renombrar los H2 redundantes como `## Objetivo de Capacitación` en vez de `## Objetivo`, o usar prefijos de contexto `## Capacitación - Objetivo`.")
    report.append("2. **Migración a pgvector (RAG semántico):** La coincidencia por cadenas exactas es extremadamente frágil. Migrar a RAG pgvector (como se describe en [ANALISIS_RAG_MULTIAGENTE.md](file:///E:/Datos/Documentos/GitHub%20Personal/DemoWhatsappAgent/ANALISIS_RAG_MULTIAGENTE.md)) resolverá esto permanentemente.")
    report.append("3. **Resolución de homónimos comerciales vs internos:** Clarificar en `facturacion.md` y `cobranza.md` que corresponden al cobro interno del cliente de DemoCorp, mientras que `democorp_modulos.md` describe los módulos del software ERP.")
    
    report.append("\n## 3. Generación de Datos Sintéticos")
    report.append("Se generó un dataset de 20 casos de prueba/QA sintéticos en `knowledge/synthetic_data.json`. Contiene preguntas realistas en lenguaje coloquial, mapeadas a su respectiva intención (`comercial`, `soporte`, `otro`), archivo de origen y respuesta exacta (ground truth).")
    report.append("\nEste dataset es ideal para evaluar la tasa de acierto del clasificador de intenciones y la precisión del recuperador RAG.")

    # Guardar reporte en el directorio de artefactos
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    report_file = ARTIFACT_DIR / "knowledge_audit.md"
    report_file.write_text("\n".join(report), encoding="utf-8")
    print(f"Reporte de auditoría escrito en {report_file}")
    
    # Generar y guardar dataset sintético
    dataset = generar_datos_sinteticos()
    with open(OUTPUT_DATASET, "w", encoding="utf-8") as out:
        json.dump(dataset, out, indent=2, ensure_ascii=False)
    print(f"Dataset de datos sintéticos escrito en {OUTPUT_DATASET}")

if __name__ == "__main__":
    main()
