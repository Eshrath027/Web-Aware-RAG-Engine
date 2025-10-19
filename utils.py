import os
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

def ingest_url_to_faiss(url: str, index_path: str, openai_key: str):
    """
    Fetches content from URL, embeds, and stores in FAISS.
    """
    loader = WebBaseLoader(url)
    docs = loader.load()
    if not docs:
        raise ValueError(f"No content found at {url}")
    
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)

    embeddings = OpenAIEmbeddings(api_key=openai_key)

    if os.path.exists(index_path):
        faiss_index = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
        faiss_index.add_documents(chunks)
    else:
        faiss_index = FAISS.from_documents(chunks, embeddings)

    faiss_index.save_local(index_path)
    return len(chunks)

