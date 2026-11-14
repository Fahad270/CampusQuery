# import os 
# from langchain_community.document_loaders import PyPDFLoader
# from langchain_text_splitters import RecursiveCharacterTextSplitter
# from langchain_google_genai import GoogleGenerativeAIEmbeddings
# from dotenv import load_dotenv
# from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_chroma import Chroma

# load_dotenv()

# filepath="./Final_Placement_Policy_2026-27.pdf"

# api_key=os.getenv("api_key")

# # Loading the data !
# def load_data(filepath):
#     loader=PyPDFLoader(file_path=filepath)

#     # It actually reads the PDF and returns LangChain Document objects.
#     documents = loader.load()

#     # if documents :
#     #     print("YES DOC EXISTS AND AINT NULL!")
#     #     print(documents[1])

#     # After Loading the documents we are converting these documents into chunks! using Recusrive Text Splitter Method from langchain! 
#     splitter= RecursiveCharacterTextSplitter(chunk_size=1000,chunk_overlap=200)
#     chunks=splitter.split_documents(documents)

#     #print("Chunks Made !! ")
#    # print(chunks)
#     return chunks 

# chunks=load_data(filepath=filepath)

# def create_embeddings():

#     embeddings = GoogleGenerativeAIEmbeddings(
#         model="gemini-embedding-001",
#         api_key=api_key
#     )

#     return embeddings

# embeddings=create_embeddings()

# '''
# def create_embeddings(chunks):

#     # Just created the model which will be used for creating the embeddings !!
#     #embeddings=GoogleGenerativeAIEmbeddings(model="gemini-embedding-001",api_key=api_key)

#     # Extracted actual text info from the doc!
#     text = [chunk.page_content for chunk in chunks]

#     # Used the embed_documents method to actually convert text into vectors!
#     # vectors=embeddings.embed_documents(text)
#     return embeddings,vectors
# vectors=create_embeddings(chunks)
# '''
# # from documents methods hi khud embeddings banake store krta haiiii !!! woh gemini ebmoeddng model was used to demomnmstat the working! bas!
# def store_inDB(chunks):
#     vectorStore=Chroma.from_documents(documents=chunks,embedding=embeddings,persist_directory="./chroma_db",collection_name="placement_policy")
#     return vectorStore

# vectorStore=store_inDB(chunks=chunks)

# print("Enter Your Doubt !")
# query = input()


# # Performing the Match ! THE ACTUAL RETRIEVAL OF THE RELATED DATA 
# # THE MAIN RAG KA RETRIEVAL PART IS BEING DONE IN THIS FUNCTION !!!!!!!
# # Extracting the most relevant  chunks k=3 

# def retrieval_data(vectorStore,query):
    
#     results=vectorStore.similarity_search(query,k=3)

#     print("Printing all the Related Information !!")

#     # for doc in results:
#     #     print(doc.page_content)
#     #     print(doc.metadata)

#     # 2. Combine retrieved chunks into context
#     context="\n\n".join([doc.page_content for doc in results])

    

#     # Model Creation !
#     model=ChatGoogleGenerativeAI(model="gemini-2.5-flash",api_key=api_key)
    
#     # Creation of the prompt !! 
#     prompt = f"""
#      You are CampusQuery, an AI assistant for college placement policies.

#     Answer the student's question using ONLY the information
#     provided in the context below.

#     Instructions:
#     - Give a clear and accurate answer.
#     - Do not make up information.
#     - If the answer is not available in the context,
#       clearly state that it is not mentioned in the placement policy.
#     - Keep the answer easy for students to understand.

#     Here is the Context : {context}

#     Here is the Student's query : {query}

#     """

#     response = model.invoke(prompt)

#     return response.content

# print("Response of the LLM : ")
# ResponseOFLLM=retrieval_data(vectorStore=vectorStore,query=query)
# print(ResponseOFLLM)



import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv
from langchain_chroma import Chroma

BASE_DIR = Path(__file__).resolve().parent

# Reuse the existing backend/.env and its api_key variable.
load_dotenv(BASE_DIR / ".env")

filepath = os.getenv(
    "POLICY_PDF",
    str(BASE_DIR / "Final_Placement_Policy_2026-27.pdf")
)

api_key=os.getenv("api_key")

COLLECTION_NAME = "placement_policy"
EMBEDDING_MODEL = "gemini-embedding-001"
CHROMA_DIR = os.getenv("CHROMA_DIR", str(BASE_DIR / "chroma_db"))
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
MANIFEST_PATH = Path(CHROMA_DIR) / "ingest_manifest.json"

logger = logging.getLogger("campusquery.ingest")

if not api_key:
    raise RuntimeError("api_key is missing from backend/.env")

# Loading the data !
def load_data(filepath):
    loader=PyPDFLoader(file_path=filepath)

    # It actually reads the PDF and returns LangChain Document objects.
    documents = loader.load()

    # if documents :
    #     print("YES DOC EXISTS AND AINT NULL!")
    #     print(documents[1])

    # After Loading the documents we are converting these documents into chunks! using Recusrive Text Splitter Method from Langchain! 
    splitter= RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE,chunk_overlap=CHUNK_OVERLAP)
    chunks=splitter.split_documents(documents)

    #print("Chunks Made !! ")
   # print(chunks)
    return chunks 

def create_embeddings():

    embeddings = GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        api_key=api_key
    )

    return embeddings

embeddings=create_embeddings()

'''
def create_embeddings(chunks):

    # Just created the model which will be used for creating the embeddings !!
    #embeddings=GoogleGenerativeAIEmbeddings(model="gemini-embedding-001",api_key=api_key)

    # Extracted actual text info from the doc!
    text = [chunk.page_content for chunk in chunks]

    # Used the embed_documents method to actually convert text into vectors!
    # vectors=embeddings.embed_documents(text)
    return embeddings,vectors
vectors=create_embeddings(chunks)
'''

# from documents methods hi khud embeddings banake store krta haiiii !!! woh gemini ebmoeddng model was used to demomnmstat the working! bas!
def store_inDB(chunks):
    vectorStore=Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DIR,
        collection_name=COLLECTION_NAME
    )
    return vectorStore


# ---------------------------------------------------------------------------
# Idempotent ingestion helpers
# ---------------------------------------------------------------------------
# A small manifest records what was indexed. Re-running ingestion for the same
# PDF is then a no-op instead of duplicating chunks and paying for embeddings.
def _file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_manifest():
    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _write_manifest(source_hash, chunk_count):
    Path(CHROMA_DIR).mkdir(parents=True, exist_ok=True)
    manifest = {
        "source": os.path.basename(filepath),
        "source_sha256": source_hash,
        "collection": COLLECTION_NAME,
        "embedding_model": EMBEDDING_MODEL,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "chunks": chunk_count,
        "ingested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    temporary = MANIFEST_PATH.with_suffix(".tmp")
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    os.replace(temporary, MANIFEST_PATH)


def _existing_store():
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR
    )


def _manifest_matches(manifest, source_hash):
    return (
        manifest is not None
        and manifest.get("source_sha256") == source_hash
        and manifest.get("collection") == COLLECTION_NAME
        and manifest.get("embedding_model") == EMBEDDING_MODEL
        and manifest.get("chunk_size") == CHUNK_SIZE
        and manifest.get("chunk_overlap") == CHUNK_OVERLAP
    )


def _existing_chunks_match(chunks):
    """Check the current collection against freshly loaded PDF chunks."""
    try:
        existing = _existing_store()
        existing_documents = existing._collection.get(include=["documents"])["documents"] or []
    except Exception:
        return False

    expected = [chunk.page_content for chunk in chunks]
    return sorted(existing_documents) == sorted(expected)


def ensure_ingested(force=False):
    """
    Ingest the policy PDF only when it is missing/changed.

    Returns (vector_store, skipped). No embedding calls are made when the
    manifest hash matches the PDF and the collection is non-empty.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Policy PDF not found: {filepath}")

    source_hash = _file_sha256(filepath)
    manifest = _read_manifest()

    if not force and _manifest_matches(manifest, source_hash):
        try:
            existing = _existing_store()
            if existing._collection.count() > 0:
                logger.info("Ingestion skipped: policy PDF is already indexed")
                return existing, True
        except Exception:
            logger.warning("Manifest matched but collection could not be read", exc_info=True)

    chunks = load_data(filepath=filepath)

    # First run against an already-populated legacy collection: seed the
    # manifest without re-embedding if its contents exactly match this PDF.
    if not force and manifest is None and _existing_chunks_match(chunks):
        _write_manifest(source_hash, len(chunks))
        logger.info("Existing ChromaDB matches the PDF; ingestion skipped")
        return _existing_store(), True

    # The PDF changed, the collection is missing, or --force was used.
    try:
        existing = _existing_store()
        existing.delete_collection()
    except Exception:
        logger.info("No existing collection to replace", exc_info=True)

    ingestion_started = time.perf_counter()
    vectorStore = store_inDB(chunks=chunks)
    elapsed_ms = (time.perf_counter() - ingestion_started) * 1000

    _write_manifest(source_hash, len(chunks))
    logger.info(
        "Ingestion complete chunks=%d elapsed=%.0fms",
        len(chunks),
        elapsed_ms
    )
    return vectorStore, False


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    if not os.path.exists(filepath):
        raise SystemExit(f"Policy PDF not found: {filepath}")

    _store, _skipped = ensure_ingested(force="--force" in sys.argv[1:])

    if _skipped:
        print("ChromaDB is already up to date. Ingestion skipped.")
    else:
        print("Successfully stored documents in ChromaDB!")
