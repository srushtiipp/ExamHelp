import json
import os

DB_PATH = "./outputs/db.json"
all_chunks = []


def store_chunks(chunks):
    global all_chunks
    all_chunks.extend(chunks)
    os.makedirs("outputs", exist_ok=True)
    with open(DB_PATH, "w") as f:
        json.dump(all_chunks, f, indent=2)
    print(f"  Saved {len(chunks)} chunks — total: {len(all_chunks)}")


def load_existing():
    global all_chunks
    if os.path.exists(DB_PATH):
        with open(DB_PATH) as f:
            all_chunks = json.load(f)
        print(f"  Loaded {len(all_chunks)} existing chunks")
    else:
        print("  No existing DB — starting fresh")


def search_chunks(query, top_k=4):
    global all_chunks
    if not all_chunks:
        return []
    query_words = query.lower().split()
    scored = []
    for chunk in all_chunks:
        text_lower = chunk["text"].lower()
        score = sum(1 for w in query_words if w in text_lower)
        scored.append({**chunk, "score": float(score)})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]
