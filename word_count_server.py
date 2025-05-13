import logging
import signal
import sys
import traceback
from collections import Counter

import rpyc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("WordCountService")


class WordCountService(rpyc.Service):
    def exposed_count_words(self, text_chunk: str) -> dict:
        """
        Count word frequencies in given text chunk.
        Returns a dictionary of word frequencies.
        """
        if not isinstance(text_chunk, str):
            logger.error(f"Expected string input, got {type(text_chunk)}")
            raise TypeError("Input must be a string")

        try:
            words = text_chunk.split()
            count = Counter(words)
            result = dict(count)
            logger.info(
                f"Processed {len(words)} words, found {len(result)} unique words"
            )
            return result
        except Exception as e:
            logger.error(f"Error processing text: {str(e)}")
            logger.error(traceback.format_exc())
            raise


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    logger.info("Shutdown signal received, stopping server...")
    sys.exit(0)


if __name__ == "__main__":
    slave_ports = [18861, 18862, 18863]

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Get port from command line argument
        if len(sys.argv) < 2:
            logger.error(
                "Port number required. Usage: python word_count_server.py PORT"
            )
            sys.exit(1)

        try:
            port = int(sys.argv[1])
            if port not in slave_ports:
                logger.error(f"Invalid port number: {port}")
                sys.exit(1)
        except ValueError:
            logger.error(f"Invalid port number: {sys.argv[1]}. Must be an integer.")
            sys.exit(1)

        # Configure server with appropriate settings
        server = rpyc.utils.server.ThreadedServer(
            WordCountService,
            port=port,
            protocol_config={
                "allow_pickle": True,
                "allow_public_attrs": True,
                "sync_request_timeout": 30,
            },
        )

        logger.info(f"Slave server starting on port {port}")
        server.start()

    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)
