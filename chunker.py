import re


def chunk_text(pages, chunk_size=350, overlap=60):
    chunks = []

    for page_data in pages:
        page_num = page_data["page"]
        text = page_data["text"]

        if not text.strip():
            continue

        sentences = re.split(r'(?<=[.!?\n])\s+', text.strip())

        current = []
        current_len = 0
        idx = 0

        for sentence in sentences:
            words = sentence.split()
            if not words:
                continue

            if current_len + len(words) > chunk_size and current:
                chunk_str = " ".join(current)

                if len(chunk_str.strip()) > 20:
                    chunks.append({
                        "id":     f"p{page_num}_c{idx}",
                        "text":   chunk_str,
                        "page":   page_num,
                        "source": f"Page {page_num}, Section {idx + 1}"
                    })

                overlap_words = " ".join(current).split()[-overlap:]
                current = overlap_words + words
                current_len = len(current)
                idx += 1

            else:
                current.extend(words)
                current_len += len(words)

        if current:
            chunk_str = " ".join(current)
            if len(chunk_str.strip()) > 20:
                chunks.append({
                    "id":     f"p{page_num}_c{idx}",
                    "text":   chunk_str,
                    "page":   page_num,
                    "source": f"Page {page_num}, Section {idx + 1}"
                })

    print(f"  Chunking done — {len(chunks)} chunks from {len(pages)} pages")
    return chunks


if __name__ == "__main__":
    sample = [{"page": 1, "text": "This is a test sentence. " * 100}]
    chunks = chunk_text(sample)
    print(f"Test passed — got {len(chunks)} chunks")
    print(f"First chunk: {chunks[0]['text'][:80]}")
