import re

filepath = "agent/tools.py"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Buscamos el inicio y fin de buscar_en_knowledge
# Starts with 'def buscar_en_knowledge(modulo: str) -> str:'
# Ends where 'def _oferta_activa' starts
start_idx = content.find("def buscar_en_knowledge")
end_idx = content.find("def _oferta_activa")

new_func = """def buscar_en_knowledge(consulta: str) -> str:
    \"\"\"Busca informacion, manuales y caracteristicas tecnicas en la base de conocimiento usando inteligencia artificial (RAG). 
    Úsalo siempre que te pregunten sobre qué hace un módulo, detalles de licencias, facturación o cualquier funcionalidad del sistema.\"\"\"
    from langchain_postgres.vectorstores import PGVector
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    
    DB_URL = os.getenv("DATABASE_URL", "postgresql://demobot:demobot@localhost:5441/demobot")
    DB_URL = DB_URL.replace("postgresql://", "postgresql+psycopg://")
    
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = PGVector(
        embeddings=embeddings,
        collection_name="democorp_knowledge",
        connection=DB_URL,
        use_jsonb=True,
    )
    
    try:
        # Recuperar los 4 fragmentos más relevantes
        resultados = vector_store.similarity_search(consulta, k=4)
        
        if not resultados:
            return "No se encontró información en la base de datos de conocimiento sobre: " + consulta
            
        texto_resultado = []
        for doc in resultados:
            fuente = doc.metadata.get("source", "Desconocida")
            fuente_nombre = Path(fuente).name if fuente != "Desconocida" else fuente
            
            # Formatear el resultado
            bloque = f"[Fuente: {fuente_nombre}]\\n{doc.page_content}\\n"
            texto_resultado.append(bloque)
            
        respuesta = "\\n\\n---\\n\\n".join(texto_resultado)
        
        # Ajuste de URL para PDFs
        public_base = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
        if public_base and ".pdf" in respuesta:
            respuesta = respuesta.replace("/static/pdfs/", f"{public_base}/static/pdfs/")
            
        return respuesta
    except Exception as e:
        logger.error(f"Fallo en busqueda RAG: {e}")
        return "Hubo un error interno al consultar la base de conocimiento."

"""

new_content = content[:start_idx] + new_func + content[end_idx:]

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_content)
