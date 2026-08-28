"""Generador de PDFs sintéticos para los módulos del ERP DemoCorp.
Crea 13 documentos PDF profesionales usando ReportLab en la carpeta static/pdfs/.
"""

import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# Directorios
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_PDF_DIR = BASE_DIR / "static" / "pdfs"
STATIC_PDF_DIR.mkdir(parents=True, exist_ok=True)

# Listado de módulos y su información
MODULOS_INFO = {
    "productos": {
        "titulo": "Módulo de Productos",
        "descripcion": "Gestión centralizada del catálogo de productos y servicios de la empresa.",
        "caracteristicas": [
            "Fichas técnicas detalladas por producto.",
            "Gestión de variantes de artículos (talla, color, etc.).",
            "Múltiples listas de precios y tarifas especiales.",
            "Generación e impresión de códigos de barras.",
            "Unidades de medida alternativas y conversiones.",
            "Configuración de combos, paquetes y kits de venta."
        ],
        "beneficios": "Optimice la estructura de su catálogo comercial y agilice el proceso de ventas mediante combos dinámicos."
    },
    "inventario": {
        "titulo": "Módulo de Inventario",
        "descripcion": "Control total del stock físico y lógico en tiempo real para múltiples bodegas.",
        "caracteristicas": [
            "Control multi-bodega con existencias independientes.",
            "Trazabilidad completa por número de lote y serie.",
            "Procesos ágiles para la realización de inventarios cíclicos.",
            "Transferencias directas y remisiones entre bodegas.",
            "Alertas automáticas de stock mínimo y máximo.",
            "Valorización automática mediante métodos PEPS y costo promedio."
        ],
        "beneficios": "Reduzca pérdidas por merma, evite quiebres de stock y conozca el valor real de su inventario al instante."
    },
    "facturacion": {
        "titulo": "Módulo de Facturación Electrónica",
        "descripcion": "Emisión rápida y segura de facturación electrónica 100% integrada con la DIAN.",
        "caracteristicas": [
            "Facturación electrónica en línea validada por la DIAN (Colombia).",
            "Generación y envío automático de notas crédito y débito.",
            "Facturación recurrente parametrizable para contratos o suscripciones.",
            "Conversión directa de remisiones y cotizaciones a facturas.",
            "Integración nativa con canales de POS y comercio electrónico.",
            "Plantillas de representación gráfica (PDF) personalizables."
        ],
        "beneficios": "Cumpla con la normativa fiscal de manera transparente, reduzca tiempos de facturación y garantice el recaudo."
    },
    "cartera": {
        "titulo": "Módulo de Cartera y Cobranza",
        "descripcion": "Control y gestión de las cuentas por cobrar a clientes de manera eficiente.",
        "caracteristicas": [
            "Reporte detallado de edades de cartera (vencimientos).",
            "Asignación y control de cupos de crédito por cliente.",
            "Registro e historial de gestiones de cobranza.",
            "Procesos de conciliación y cruce de pagos automáticos.",
            "Recordatorios de pago automáticos vía correo y WhatsApp.",
            "Estados de cuenta interactivos para clientes."
        ],
        "beneficios": "Mejore la liquidez de su caja, disminuya la cartera vencida y automatice el seguimiento de deudores."
    },
    "compras": {
        "titulo": "Módulo de Compras",
        "descripcion": "Gestión del proceso de adquisición de insumos y productos con proveedores.",
        "caracteristicas": [
            "Generación y seguimiento de órdenes de compra.",
            "Comparativo de cotizaciones y ofertas de proveedores.",
            "Recepción física y lógica de mercancías con cruce de factura.",
            "Flujos de aprobación de órdenes de compra según presupuesto.",
            "Historial de precios de compra por proveedor.",
            "Control de entregas parciales de órdenes activas."
        ],
        "beneficios": "Optimice la relación con sus proveedores, controle los costos de compra y evite compras no autorizadas."
    },
    "cuentas_por_pagar": {
        "titulo": "Módulo de Cuentas por Pagar",
        "descripcion": "Gestión y control de compromisos financieros y pagos a proveedores.",
        "caracteristicas": [
            "Programación y proyección de pagos a proveedores.",
            "Causación automática desde compras y facturas de gasto.",
            "Control de retenciones en la fuente aplicables.",
            "Flujo de aprobación interna de facturas de proveedores.",
            "Historial detallado de saldos pendientes y pagos realizados.",
            "Integración con el módulo de tesorería para desembolsos."
        ],
        "beneficios": "Evite cargos por mora, planifique sus salidas de efectivo y mantenga relaciones sólidas con sus proveedores."
    },
    "tesoreria": {
        "titulo": "Módulo de Tesorería",
        "descripcion": "Administración de cuentas bancarias, flujo de caja y control de cajas menores.",
        "caracteristicas": [
            "Conciliación bancaria automática mediante carga de extractos.",
            "Proyección del flujo de caja (Cash Flow) en tiempo real.",
            "Soporte multi-moneda para cuentas bancarias.",
            "Gestión y control de chequeras y transferencias bancarias.",
            "Control de arqueo de cajas menores y desembolsos.",
            "Generación de soportes de egreso y recibos de caja."
        ],
        "beneficios": "Tenga visibilidad absoluta del saldo disponible en sus bancos, automatice conciliaciones y controle gastos menores."
    },
    "importaciones": {
        "titulo": "Módulo de Importaciones",
        "descripcion": "Gestión operativa y costeo de compras internacionales e importaciones.",
        "caracteristicas": [
            "Control y seguimiento de trámites aduaneros y documentos (DEX).",
            "Prorrateo y costeo de gastos de importación (fletes, seguros).",
            "Seguimiento logístico de embarques y fechas de arribo.",
            "Liquidación automática de impuestos de nacionalización.",
            "Cruce automático con órdenes de compra internacionales.",
            "Asignación de costo real de nacionalización al inventario."
        ],
        "beneficios": "Conozca el costo unitario realizado de sus productos importados incluyendo aranceles y transporte."
    },
    "crm": {
        "titulo": "Módulo CRM Comercial",
        "descripcion": "Gestión de la relación con clientes y control del embudo de ventas comercial.",
        "caracteristicas": [
            "Registro y segmentación de leads y clientes potenciales.",
            "Pipeline de ventas visual por etapas del embudo comercial.",
            "Historial completo de interacciones (llamadas, correos, notas).",
            "Gestión y asignación de tareas de seguimiento comercial.",
            "Diseño y envío de campañas comerciales segmentadas.",
            "Reportes de conversión y efectividad de asesores."
        ],
        "beneficios": "Aumente el cierre de ventas, brinde un seguimiento impecable a prospectos y ordene su equipo comercial."
    },
    "produccion": {
        "titulo": "Módulo de Producción",
        "descripcion": "Planeación, control de costos y manufactura de productos terminados.",
        "caracteristicas": [
            "Creación de órdenes de producción y planeación de lotes.",
            "Listas de materiales detalladas (BOM - Bill of Materials).",
            "Control preciso de costos de fabricación (materia prima, mano de obra).",
            "Planeación y análisis de capacidad de planta.",
            "Controles de calidad en fases del proceso de manufactura.",
            "Consumo automático de insumos al cerrar órdenes."
        ],
        "beneficios": "Domine los costos de fabricación de sus productos y maximice el rendimiento de sus insumos y mano de obra."
    },
    "nomina": {
        "titulo": "Módulo de Nómina Electrónica",
        "descripcion": "Liquidación y emisión de nómina electrónica validada ante la DIAN.",
        "caracteristicas": [
            "Liquidación periódica de nómina y seguridad social.",
            "Emisión y validación de nómina electrónica ante la DIAN.",
            "Procesamiento de novedades (vacaciones, incapacidades, horas extra).",
            "Cálculo y provisión de prestaciones sociales.",
            "Control de préstamos al personal y descuentos automáticos.",
            "Generación automática de certificados laborales."
        ],
        "beneficios": "Cumpla con la nómina electrónica legal, evite sanciones de la UGPP y liquide salarios sin errores."
    },
    "contabilidad": {
        "titulo": "Módulo de Contabilidad NIIF",
        "descripcion": "Generación de estados financieros y contabilidad automatizada integrada.",
        "caracteristicas": [
            "Plan único de cuentas (PUC) totalmente configurable.",
            "Causación contable automática en tiempo real desde otros módulos.",
            "Generación de estados financieros bajo estándares NIIF.",
            "Control de presupuestos y centros de costo por departamento.",
            "Generación de informes para medios magnéticos (Exógena).",
            "Cierre automático de períodos mensuales y anuales."
        ],
        "beneficios": "Elimine la digitación contable duplicada, obtenga balances al día y facilite auditorías fiscales."
    },
    "pos": {
        "titulo": "Módulo de Punto de Venta (POS)",
        "descripcion": "Facturación rápida en mostradores y locales de venta al público.",
        "caracteristicas": [
            "Interfaz táctil optimizada para cajeros de venta rápida.",
            "Soporte de múltiples medios de pago (efectivo, tarjetas, billeteras).",
            "Gestión de turnos de caja, bases y cierres (arqueo de caja).",
            "Facturación electrónica en línea o tirilla POS en contingencia.",
            "Sincronización de existencias de inventario en tiempo real.",
            "Conexión con cajones monederos, balanzas e impresoras térmicas."
        ],
        "beneficios": "Agilice las filas en sus puntos de venta, evite descuadres de caja y mantenga su inventario al día."
    }
}

def generar_pdf(name, data):
    pdf_path = STATIC_PDF_DIR / f"{name}.pdf"
    
    # Configurar documento (Márgenes de 0.5 in)
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Estilos corporativos personalizados
    primary_color = colors.HexColor("#1A365D") # Navy blue
    secondary_color = colors.HexColor("#3182CE") # Light blue
    text_color = colors.HexColor("#2D3748") # Charcoal
    
    styles.add(ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=primary_color,
        spaceAfter=6
    ))
    
    styles.add(ParagraphStyle(
        'DocSubtitle',
        parent=styles['Heading2'],
        fontName='Helvetica',
        fontSize=12,
        textColor=secondary_color,
        spaceAfter=15
    ))
    
    styles.add(ParagraphStyle(
        'BodyCharcoal',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=10.5,
        textColor=text_color,
        leading=14,
        spaceAfter=10
    ))
    
    styles.add(ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=14,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=6
    ))
    
    styles.add(ParagraphStyle(
        'BulletItem',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=text_color,
        leading=13,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    ))
    
    styles.add(ParagraphStyle(
        'FooterText',
        fontName='Helvetica-Oblique',
        fontSize=8,
        textColor=colors.HexColor("#718096"),
        alignment=1 # Center
    ))

    story = []
    
    # 1. Encabezado corporativo (Barra de color)
    header_data = [[Paragraph("<b>DemoCorp ERP</b> | Soluciones de Software Empresarial", ParagraphStyle('HText', fontName='Helvetica-Bold', fontSize=10, textColor=colors.white))]]
    header_table = Table(header_data, colWidths=[540])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), primary_color),
        ('PADDING', (0,0), (-1,-1), 8),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 15))
    
    # 2. Título y Subtítulo
    story.append(Paragraph(data["titulo"], styles['DocTitle']))
    story.append(Paragraph("Ficha Técnica de Módulo Oficial de DemoCorp ERP", styles['DocSubtitle']))
    
    # 3. Descripción General
    story.append(Paragraph("<b>Descripción General:</b>", styles['SectionHeader']))
    story.append(Paragraph(data["descripcion"], styles['BodyCharcoal']))
    
    # 4. Características Principales
    story.append(Paragraph("<b>Características Principales:</b>", styles['SectionHeader']))
    for feat in data["caracteristicas"]:
        story.append(Paragraph(f"&bull; {feat}", styles['BulletItem']))
    story.append(Spacer(1, 8))
    
    # 5. Beneficios de Implementación
    story.append(Paragraph("<b>Beneficios para su Empresa:</b>", styles['SectionHeader']))
    story.append(Paragraph(data["beneficios"], styles['BodyCharcoal']))
    
    # 6. Tabla de Licenciamiento y Soporte
    story.append(Paragraph("<b>Condiciones de Servicio y Soporte:</b>", styles['SectionHeader']))
    conditions_data = [
        ["Modalidad de Pago", "Anual por suscripción"],
        ["Soporte Técnico", "Incluido sin costo adicional durante el año de vigencia"],
        ["Actualizaciones", "Acceso gratuito a últimas versiones de software"],
        ["Canales de Soporte", "Chatbot WhatsApp 24/7, soporte por correo y acceso técnico remoto"]
    ]
    cond_table = Table(conditions_data, colWidths=[150, 390])
    cond_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor("#EDF2F7")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('PADDING', (0,0), (-1,-1), 6),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (1,0), (1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9.5),
        ('TEXTCOLOR', (0,0), (-1,-1), text_color),
    ]))
    story.append(cond_table)
    story.append(Spacer(1, 20))
    
    # Divider line
    divider = Table([[""]], colWidths=[540])
    divider.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,-1), 1, colors.HexColor("#E2E8F0")),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(divider)
    story.append(Spacer(1, 10))
    
    # 7. Pie de página de contacto
    story.append(Paragraph("<b>Contacto Comercial:</b> comercial@democorp.com | <b>Soporte Técnico:</b> soporte@democorp.com", styles['FooterText']))
    story.append(Paragraph("DemoCorp ERP &copy; 2026 - Todos los derechos reservados. Colombia.", styles['FooterText']))
    
    # Construir PDF
    doc.build(story)
    print(f"PDF generado: {pdf_path.name}")

if __name__ == "__main__":
    print("Iniciando generación de PDFs de módulos...")
    for name, data in MODULOS_INFO.items():
        generar_pdf(name, data)
    print("Generación finalizada con éxito.")
