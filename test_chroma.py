import chromadb
client = chromadb.Client()
col = client.create_collection("test")
try:
    col.upsert(ids=["1"], documents=["abc"], metadatas=[{"type": ""}])
    print("Empty string allowed")
except Exception as e:
    print("Error:", e)
try:
    col.upsert(ids=["2"], documents=["def"], metadatas=[{"type": None, "foo": "bar"}])
    print("None allowed")
except Exception as e:
    print("Error:", e)
try:
    col.upsert(ids=["3"], documents=["ghi"], metadatas=[{"project_id": "123"}])
    print("Normal allowed")
except Exception as e:
    print("Error:", e)
