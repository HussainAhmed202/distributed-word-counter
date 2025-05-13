from collections import Counter

import rpyc
from rpyc.utils.classic import obtain

# Read book text
try:
    with open("data/sample.txt", "r") as f:
        book_text = f.read()
except FileNotFoundError:
    print("[ERROR] File 'data/sample.txt' not found.")
    exit(1)
except UnicodeDecodeError:
    print(
        f"Error: Unable to decode file 'data/sample.txt'. Try specifying the correct encoding."
    )
    exit(1)


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
    # print(type(word_counts))   <netref class 'rpyc.core.netref.builtins.dict'>

    # typecast into dictionary
    word_counts = obtain(word_counts)
    # print(type(word_counts))  # Should now print <class 'dict'>

    results.append(word_counts)

final_counts = Counter()
for r in results:
    final_counts.update(r)

print(final_counts.most_common(10))
