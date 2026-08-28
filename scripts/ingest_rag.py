import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_postgres.vectorstores import PGVector

# Cargar variables
load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://demobot:demobot@localhost:5441/demobot")
# PGVector uses psycopg3 syntax mostly, so format might need to be adjusted:
DB_URL = DB_URL.replace("postgresql://", "postgresql+psycopg://")

COLLECTION_NAME = "democorp_knowledge"

KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"
PDF_DIR = Path(__file__).parent.parent / "static" / "pdfs"

async def main():
    print("Iniciando ingesta de RAG...")
    
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    
    # Initialize PGVector
    # The new langchain_postgres module takes a connection string directly.
    vector_store = PGVector(
        embeddings=embeddings,
        collection_name=COLLECTION_NAME,
        connection=DB_URL,
        use_jsonb=True,
    )
    
    # 1. Cargar Markdowns
    print("Cargando Markdowns desde /knowledge...")
    md_docs = []
    for md_file in KNOWLEDGE_DIR.glob("*.md"):
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
            # UnstructuredMarkdownLoader a veces puede ser ruidoso con metadatos.
            # Usaremos una carga simple.
            from langchain_core.documents import Document
            md_docs.append(Document(page_content=content, metadata={"source": str(md_file), "type": "markdown"}))
        except Exception as e:
            print(f"Error cargando {md_file}: {e}")
            
    # 2. Cargar PDFs
    print("Cargando PDFs desde /static/pdfs...")
    pdf_docs = []
    for pdf_file in PDF_DIR.glob("*.pdf"):
        try:
            loader = PyPDFLoader(str(pdf_file))
            docs = loader.load()
            for d in docs:
                d.metadata["type"] = "pdf"
            pdf_docs.extend(docs)
        except Exception as e:
            print(f"Error cargando {pdf_file}: {e}")
            
    all_docs = md_docs + pdf_docs
    print(f"Total documentos cargados: {len(all_docs)} (paginas/archivos)")
    
    # 3. Fragmentar Textos (Chunking)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    
    chunks = text_splitter.split_documents(all_docs)
    print(f"Total fragmentos generados (chunks): {len(chunks)}")
    
    # 4. Ingestar
    print("Generando embeddings y guardando en PostgreSQL (pgvector)...")
    # Limpiamos la coleccion antes de insertar (opcional)
    vector_store.drop_tables()
    vector_store.create_tables_if_not_exists()
    
    batch_size = 50
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        print(f"  Insertando lote {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1}...")
        vector_store.add_documents(batch)
        
    print("Ingesta RAG completada con exito.")

if __name__ == "__main__":
    asyncio.run(main())