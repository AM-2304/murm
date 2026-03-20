import chromadb
client = chromadb.Client()
col = client.create_collection("test")
try:
    col.upsert(ids=[], documents=[], metadatas=[])
    print("Empty list allowed")
except Exception as e:
    print("Error:", e)
