# master_node.py
from collections import Counter

import rpyc
from rpyc.utils.classic import obtain

# Read book text
with open("data/sample.txt", "r") as f:
    book_text = f.read()


def split_text(text, num_chunks):
    words = text.split()
    chunk_size = len(words) // num_chunks
    return [
        " ".join(words[i * chunk_size : (i + 1) * chunk_size])
        for i in range(num_chunks)
    ]


# Define local slave ports
slave_ports = [18861, 18862, 18863]
chunks = split_text(book_text, len(slave_ports))

# Connect and send tasks
results = []
for port, chunk in zip(slave_ports, chunks):
    conn = rpyc.connect("localhost", port)
    print(f"Connected to slave on port {port}")
    word_counts = conn.root.count_words(chunk)
    print(type(word_counts))  # <netref class 'rpyc.core.netref.builtins.dict'>

    print(word_counts.items())

    # results.append(obtain(word_counts)) # typcase to dic

    # results.append(word_counts)

final_counts = Counter()
for r in results:
    final_counts.update(r)

print(final_counts.most_common(10))
