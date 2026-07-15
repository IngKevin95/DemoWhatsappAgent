# Base de errores y fallas comunes SysPlus ERP

## Factura electrónica rechazada por DIAN - Error común

**Síntomas:** La factura electrónica queda con estado rechazada por la DIAN o no se genera el código CUFE.

### Causas frecuentes:
- Datos fiscales del cliente adquiriente incompletos o erróneos.
- Resolución DIAN vencida o sin rango de numeración disponible.
- Certificado digital de la empresa vencido.
- Errores de parametrización tributaria en impuestos o retenciones.

**Respuesta sugerida:** Recomendar validar los datos fiscales del cliente, vigencia de resolución DIAN, validez del certificado digital y parametrización de impuestos. Si persiste y tiene código de error DIAN, solicitarlo para radicar ticket de soporte.

---

## Producto sin stock al facturar - Error común

**Síntomas:** El sistema bloquea la venta del producto o arroja alerta de inventario insuficiente.

### Causas frecuentes:
- Existencias ubicadas en una bodega diferente a la seleccionada para la venta.
- Facturas de compra o entradas de inventario no guardadas/contabilizadas.
- Unidades de inventario reservadas por pedidos de clientes previos.
- Descuadres entre el inventario físico y las cantidades registradas en el sistema.

**Respuesta sugerida:** Indicar revisión de existencias por bodega, verificar reservas y validar que las últimas entradas estén contabilizadas. En caso de diferencia física, realizar conteo físico y ajuste.

---

## No aparece un pago en cartera - Error común

**Síntomas:** La factura sigue reflejando saldo pendiente a pesar de que el cliente reporta haber realizado el pago.

### Causas frecuentes:
- Recibo de caja ingresado en tesorería pero no aplicado a la factura en cartera.
- Consignaciones o transferencias bancarias recibidas sin identificar (pendientes de conciliar).
- Diferencias de centavos o valores menores en el pago recibido.
- Recibo de caja aplicado a una factura o cliente erróneo.

**Respuesta sugerida:** Solicitar soporte de pago (fecha, banco, valor) y validar en tesorería el estado de la conciliación bancaria y la correcta aplicación del recibo de caja.

---

## POS no sincroniza ventas - Error común

**Síntomas:** Las ventas registradas en el punto de venta local (POS) no se reflejan en el ERP central.

### Causas frecuentes:
- Pérdida de conexión a internet en el equipo POS del punto de venta.
- Turno de caja actual no cerrado o acumulado de días anteriores sin cerrar.
- Servicio de sincronización local del POS detenido en el sistema operativo.
- Credenciales de acceso del POS expiradas.

**Respuesta sugerida:** Validar conexión a internet del punto, confirmar cierre de turnos del día y revisar el estado del servicio de sincronización. Si continúa, tomar datos de la sede y caja para radicar caso de soporte.

---

## Usuario no puede ingresar - Error común

**Síntomas:** Credenciales rechazadas en el inicio de sesión o pantalla de carga bloqueada indefinidamente.

### Causas frecuentes:
- Contraseña o nombre de usuario incorrectos (sensible a mayúsculas).
- Usuario inactivo en el panel de administración.
- Perfil de usuario sin permisos de acceso configurados.
- Bloqueo temporal de la cuenta por intentos de inicio fallidos.

**Respuesta sugerida:** Recomendar restablecimiento de contraseña al administrador del sistema y verificar que el usuario esté activo. Si es por permisos, solicitar captura del error indicando módulo al que intenta acceder.

---

## Reporte contable no cuadra - Error común

**Síntomas:** Diferencias de saldos en balances, auxiliares contables o estados financieros.

### Causas frecuentes:
- Documentos de venta, compra o tesorería guardados pero sin procesar la contabilización automática.
- Periodos contables cerrados de forma parcial con movimientos pendientes.
- Parametrización contable de cuentas contables incorrecta por módulo.
- Documentos cargados sin tercero o centro de costos asignados.

**Respuesta sugerida:** Sugerir ejecutar el proceso de contabilización automática de lotes pendientes, validar parametrización de cuentas en los módulos origen y revisar reportes auxiliares de descuadres.

---

## Lentitud general del sistema - Falla común

**Síntomas:** Demora excesiva en la carga de pantallas, consultas o al generar reportes pesados.

### Causas frecuentes:
- Consulta de reportes con rangos de fechas excesivamente amplios (ej. varios años).
- Sobrecarga de usuarios generando de forma concurrente reportes masivos.
- Conexión a internet inestable o con baja velocidad de subida/bajada.
- Acumulación de memoria caché y cookies en el navegador web del usuario.

**Respuesta sugerida:** Recomendar limpiar la caché del navegador, probar la conexión de red y realizar consultas delimitando rangos de fechas cortos (ej. mes actual). Si es en un proceso específico, tomar hora del evento y módulo para revisar logs.
