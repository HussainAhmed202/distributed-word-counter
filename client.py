import os
import string
import sys
import time
from collections import Counter

import nltk
import rpyc
from rpyc.utils.classic import obtain


def preprocess_text(text: str) -> str:
    """Preprocess text by removing punctuation,
    numbers, stopwords and converting to lowercase and return cleaned text
    """

    # nltk.download("punkt")

    # break into words
    tokens = nltk.word_tokenize(text)

    # convert to lower case and remove numbers
    tokens = [token.lower() for token in tokens if token.isalpha()]

    # remove stop words
    # nltk.download("stopwords")
    stop_words = set(nltk.corpus.stopwords.words("english"))
    tokens = [token for token in tokens if token not in stop_words]

    # remove punctuation
    tokens = [token for token in tokens if token not in string.punctuation]
    return " ".join(tokens)


def load_text(filepath):
    """Load text from file with error handling"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found.")
        sys.exit(1)
    # except PermissionError:
    #     print(f"Error: Permission denied when trying to read '{filepath}'.")
    #     sys.exit(1)
    except UnicodeDecodeError:
        print(
            f"Error: Unable to decode file '{filepath}'. Try specifying the correct encoding."
        )
        sys.exit(1)
    except IOError as e:
        print(f"Error reading file: {str(e)}")
        return
    # except Exception as e:
    #     print(f"Unexpected error reading file: {str(e)}")
    #     sys.exit(1)


def split_text(text, num_chunks):
    """Split text into approximately equal chunks"""
    words = text.split()

    # Handle case where there are fewer words than chunks
    try:
        if len(words) < num_chunks:
            print(
                f"Warning: Text has fewer words ({len(words)}) than requested chunks ({num_chunks})."
            )
            num_chunks = min(len(words), num_chunks)

        chunk_size = max(1, len(words) // num_chunks)
    except ZeroDivisionError:
        print("Error: Text is empty or contains only whitespace or only numbers.")
        sys.exit(1)

    chunks = []

    for i in range(num_chunks - 1):
        chunks.append(" ".join(words[i * chunk_size : (i + 1) * chunk_size]))

    # Last chunk gets any remaining words
    chunks.append(" ".join(words[(num_chunks - 1) * chunk_size :]))

    return chunks


def connect_to_slave(host, port, retries=3, retry_delay=10):
    """Connect to a slave with retry logic"""
    for attempt in range(retries):
        try:
            conn = rpyc.connect(host, port, config={"sync_request_timeout": 30})
            print(f"Connected to slave at {host}:{port}")
            return conn
        except ConnectionRefusedError:
            print(
                f"Connection refused to slave at {host}:{port}. Is the server running? Attempt {attempt+1}/{retries}"
            )
            if attempt < retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(
                    f"Failed to connect to slave on port {port} after {retries} attempts."
                )
                raise
        except Exception as e:
            print(f"Unexpected error connecting to port {port}: {str(e)}")
            raise


# def process_chunk(host, port, chunk):
#     """Process a text chunk on a specific slave"""
#     try:
#         conn = connect_to_slave(host, port)

#         try:
#             # Get word counts from remote service
#             word_counts = conn.root.count_words(chunk)

#             # Convert netref object to local object
#             try:
#                 word_counts = obtain(word_counts)
#                 return word_counts
#             except Exception as e:
#                 print(f"Error obtaining result from port {port}: {str(e)}")
#                 raise

#         except rpyc.core.protocol.PingError:
#             print(f"Connection lost to slave on port {port} during processing")
#             raise
#         except Exception as e:
#             print(f"Error during remote processing on port {port}: {str(e)}")
#             raise
#         finally:
#             # Always try to close the connection
#             conn.close()

#     except Exception as e:
#         print(f"Failed to process chunk on port {port}: {str(e)}")
#         return Counter()  # Return empty counter on failure


def process_chunk(port, chunk):
    """Process a text chunk on a specific slave"""
    try:
        conn = connect_to_slave("localhost", port)

        try:
            # Get word counts from remote service
            word_counts = conn.root.count_words(chunk)

            # Convert netref object to local object
            try:
                word_counts = obtain(word_counts)
                return word_counts
            except Exception as e:
                print(f"Error obtaining result from port {port}: {str(e)}")
                raise

        except rpyc.core.protocol.PingError:
            print(f"Connection lost to slave on port {port} during processing")
            raise
        except Exception as e:
            print(f"Error during remote processing on port {port}: {str(e)}")
            raise
        finally:
            # Always try to close the connection
            conn.close()

    except Exception as e:
        print(f"Failed to process chunk on port {port}: {str(e)}")
        return Counter()  # Return empty counter on failure


# def main():
# input_file = "data/sample.txt"

# # Configuration
# # slave_servers = [
# #     ("172.31.35.88", 18861),
# #     ("172.31.35.148", 18862),
# #     ("172.31.39.162", 18863),
# # ]

# ports = [18861, 18862, 18863]

# # Load text
# try:
#     book_text = load_text(input_file)
#     print(f"Successfully loaded text from {input_file}")
# except SystemExit:
#     sys.exit(1)  # Exit if file loading failed

# # Split text into chunks
# # chunks = split_text(book_text, len(slave_servers))
# chunks = split_text(book_text, len(ports))

# print(f"Split text into {len(chunks)} chunks")

# # Connect and send tasks
# results: list[dict] = []
# # for (host, port), chunk in zip(slave_servers, chunks):
# #     try:
# #         word_counts = process_chunk(host, port, chunk)
# #         if word_counts:
# #             results.append(word_counts)
# #             print(f"Successfully processed chunk on port {port}")
# #         else:
# #             print(f"No results from slave on port {port}")
# #     except Exception as e:
# #         print(f"Failed to process on port {port}: {e}")

# for port, chunk in zip(ports, chunks):
#     try:
#         word_counts = process_chunk(port, chunk)
#         if word_counts:
#             results.append(word_counts)
#             print(f"Successfully processed chunk on port {port}")
#         else:
#             print(f"No results from slave on port {port}")
#     except Exception as e:
#         print(f"Failed to process on port {port}: {e}")

# # Combine results
# if not results:
#     print("Error: No results collected from any slaves.")
#     sys.exit(1)

# # aggregate result
# final_counts = Counter()
# for r in results:
#     final_counts.update(r)

# # print(f"\nProcessed {sum(results.values())} words across {len(results)} slaves")
# print("\nTop 10 most common words:")
# print("-" * 30)
# # for word, count in results.most_common(10):
# #     print(f"{word}: {count}")

# for word, count in final_counts.most_common(10):
#     print(f"{word}: {count}")
