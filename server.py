# word_count_server.py
import sys
from collections import Counter

import rpyc


class WordCountService(rpyc.Service):
    def exposed_count_words(self, text_chunk: str) -> dict[str:int]:
        words = text_chunk.split()
        count = Counter(words)
        return dict(count)


if __name__ == "__main__":
    from rpyc.utils.server import ThreadedServer

    port = int(sys.argv[1])  # Pass port as argument
    server = ThreadedServer(WordCountService, port=port)
    print(f"Slave running on port {port}")
    server.start()
