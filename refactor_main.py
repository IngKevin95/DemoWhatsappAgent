import re

def refactor_main():
    with open('agent/main.py', 'r', encoding='utf-8') as f:
        code = f.read()

    # 1. Update the webhook definitions to use `proveedor_meta`
    code = code.replace(
        "challenge = proveedor.validar_webhook(dict(request.query_params))",
        "challenge = proveedor_meta.validar_webhook(dict(request.query_params))"
    )
    code = code.replace(
        "if not proveedor.validar_firma(cuerpo, firma):",
        "if not proveedor_meta.validar_firma(cuerpo, firma):"
    )
    code = code.replace(
        "mensaje = proveedor.parsear_webhook(payload)",
        "mensaje = proveedor_meta.parsear_webhook(payload)"
    )

    # 2. Extract common logic into procesar_mensaje_entrante
    body_to_extract_pattern = r"    if mensaje is None:\n        return \{\"status\": \"ignorado\"\}\n\n    from \.memory import abrir_conversacion(.*?)await enviar_mensaje_seguro\(mensaje\.telefono, respuesta\)\n    return \{\"status\": \"ok\"\}"
    
    match = re.search(body_to_extract_pattern, code, re.DOTALL)
    if not match:
        print("Could not find the webhook body")
        return
        
    extracted_body = match.group(0)
    
    # We need to change the Contacto creation to include canal
    extracted_body = extracted_body.replace(
        "contacto = Contacto(telefono=mensaje.telefono, nombre=mensaje.telefono, consentimiento_datos=False)",
        "contacto = Contacto(telefono=mensaje.telefono, nombre=mensaje.nombre or mensaje.telefono, consentimiento_datos=False, canal=canal)"
    )
    
    # Also we need to make sure enviar_mensaje_seguro calls use canal=canal inside the common logic
    extracted_body = extracted_body.replace(
        "await enviar_mensaje_seguro(mensaje.telefono, \"Gracias. Hemos registrado tu consentimiento. ¿En qué te puedo ayudar?\")",
        "await enviar_mensaje_seguro(mensaje.telefono, \"Gracias. Hemos registrado tu consentimiento. ¿En qué te puedo ayudar?\", canal=canal)"
    )
    extracted_body = extracted_body.replace(
        "await enviar_mensaje_seguro(mensaje.telefono, \"Entendemos. No podemos procesar tus datos sin tu consentimiento. Hasta pronto.\")",
        "await enviar_mensaje_seguro(mensaje.telefono, \"Entendemos. No podemos procesar tus datos sin tu consentimiento. Hasta pronto.\", canal=canal)"
    )
    extracted_body = extracted_body.replace(
        "botones=botones\n            )",
        "botones=botones,\n                canal=canal\n            )"
    )
    extracted_body = extracted_body.replace(
        "await enviar_mensaje_seguro(mensaje.telefono, respuesta)",
        "await enviar_mensaje_seguro(mensaje.telefono, respuesta, canal=canal)"
    )

    common_func = f"""async def procesar_mensaje_entrante(mensaje, canal="meta"):
{extracted_body}
"""
    
    # Replace the old receiving part
    new_recibir_meta = """    if mensaje is None:
        return {"status": "ignorado"}
    
    return await procesar_mensaje_entrante(mensaje, canal="meta")"""
    
    code = code.replace(match.group(0), new_recibir_meta)
    
    # Insert the common function right before the webhook
    code = code.replace("@app.get(\"/webhook\")", common_func + "\n\n@app.get(\"/webhook\")")
    
    # 3. Add Telegram webhooks
    telegram_webhooks = """
@app.get("/webhook/telegram")
async def verificar_webhook_telegram(request: Request):
    challenge = proveedor_telegram.validar_webhook(dict(request.query_params))
    if challenge:
        return PlainTextResponse(challenge)
    return PlainTextResponse("Token inválido", status_code=403)

@app.post("/webhook/telegram")
async def recibir_webhook_telegram(request: Request):
    cuerpo = await request.body()
    firma = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if not proveedor_telegram.validar_firma(cuerpo, firma):
        return PlainTextResponse("Firma inválida", status_code=403)

    payload = await request.json()
    mensaje = proveedor_telegram.parsear_webhook(payload)
    if mensaje is None:
        return {"status": "ignorado"}
        
    return await procesar_mensaje_entrante(mensaje, canal="telegram")
"""
    
    # Add telegram endpoints before liberar_agente
    code = code.replace("@app.post(\"/agentes/{telefono_cliente}/liberar\")", telegram_webhooks + "\n@app.post(\"/agentes/{telefono_cliente}/liberar\")")
    
    # 4. Update liberar_agente to use the correct provider
    liberar_agente_update = """
    with SyncSession() as session:
        contacto = session.query(Contacto).filter(Contacto.telefono == telefono_cliente).first()
        canal = contacto.canal if contacto else "meta"
        
    await enviar_mensaje_seguro(telefono_cliente, MENSAJE_REACTIVACION, canal=canal)
"""
    code = code.replace("await proveedor.enviar_mensaje(telefono_cliente, MENSAJE_REACTIVACION)", liberar_agente_update.strip())
    
    with open('agent/main.py', 'w', encoding='utf-8') as f:
        f.write(code)
        
    print("Refactor complete!")

if __name__ == '__main__':
    refactor_main()
