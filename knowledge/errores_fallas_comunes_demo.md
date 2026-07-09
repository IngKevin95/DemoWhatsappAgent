# Base demo de errores y fallas comunes SysPlus ERP

## Error: factura electrónica rechazada por DIAN
Síntomas: la factura queda rechazada o no genera CUFE.

Causas frecuentes:
- Datos fiscales del cliente incompletos.
- Resolución DIAN vencida o sin numeración disponible.
- Certificado digital vencido.
- Impuestos o retenciones mal configurados.

Respuesta sugerida:
Indica al usuario que valide datos del cliente, resolución DIAN, certificado digital y configuración tributaria. Si el rechazo trae código DIAN, pedir el código exacto para crear ticket.

## Error: producto sin stock al facturar
Síntomas: el sistema no permite vender o muestra inventario insuficiente.

Causas frecuentes:
- Producto en otra bodega.
- Entrada de compra no contabilizada.
- Inventario reservado por pedido.
- Diferencia entre inventario físico y sistema.

Respuesta sugerida:
Recomendar revisar existencias por bodega, reservas, últimas entradas y movimientos del producto. Si hay diferencia física, sugerir inventario cíclico.

## Error: no aparece un pago en cartera
Síntomas: la factura sigue vencida aunque el cliente dice que pagó.

Causas frecuentes:
- Pago registrado en Tesorería pero no aplicado a cartera.
- Consignación sin identificar.
- Diferencia en valor pagado.
- Pago aplicado a otro cliente o factura.

Respuesta sugerida:
Pedir fecha, valor, banco y comprobante. Sugerir revisar conciliación bancaria y aplicación del recibo de caja.

## Error: POS no sincroniza ventas
Síntomas: ventas del punto no aparecen en el ERP central.

Causas frecuentes:
- Sin conexión a internet.
- Turno de caja no cerrado.
- Servicio de sincronización detenido.
- Credenciales del POS vencidas.

Respuesta sugerida:
Pedir que validen conexión, cierre de turno y estado de sincronización. Si persiste, crear ticket con sede, caja y hora del último intento.

## Error: usuario no puede ingresar
Síntomas: credenciales rechazadas o pantalla queda cargando.

Causas frecuentes:
- Contraseña incorrecta.
- Usuario inactivo.
- Perfil sin permisos.
- Bloqueo temporal por intentos fallidos.

Respuesta sugerida:
Recomendar restablecer contraseña y validar estado del usuario. Si es tema de permisos, pedir módulo y acción que intenta realizar.

## Error: reporte contable no cuadra
Síntomas: balance, auxiliar o estado financiero muestra diferencias.

Causas frecuentes:
- Documentos sin contabilizar.
- Periodo contable cerrado parcialmente.
- Cuentas mal parametrizadas.
- Terceros o centros de costo incompletos.

Respuesta sugerida:
Sugerir ejecutar proceso de contabilización, revisar documentos pendientes y validar parametrización contable por módulo.

## Falla común: lentitud general del sistema
Síntomas: pantallas cargan lento o reportes tardan demasiado.

Causas frecuentes:
- Filtros de fecha muy amplios.
- Muchos usuarios generando reportes pesados.
- Conexión inestable.
- Navegador con caché saturada.

Respuesta sugerida:
Pedir módulo, hora del evento y acción exacta. Recomendar probar con rango de fechas menor y limpiar caché antes de escalar.
