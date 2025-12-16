import json
import time
from datetime import datetime
from random import randint

from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

from .common import BOOTSTRAP_SERVERS, TOPIC


def wait_for_kafka(max_retries: int = 30, delay: int = 2) -> None:
    """Attende che Kafka sia disponibile prima di procedere."""
    for i in range(max_retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers=BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                api_version=(0, 10, 1),
            )
            producer.close()
            print("Kafka is ready!")
            return
        except NoBrokersAvailable:
            if i < max_retries - 1:
                print(f"Waiting for Kafka... (attempt {i+1}/{max_retries})")
                time.sleep(delay)
            else:
                raise


def main() -> None:
    wait_for_kafka()
    
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    i = 0
    while True:
        message = {"index": i, "timestamp": datetime.utcnow().isoformat()}
        producer.send(TOPIC, value=message)
        producer.flush()
        delay = randint(10, 100)
        print(f"Produced: {message} | next in {delay} seconds")
        i += 1
        time.sleep(delay)


if __name__ == "__main__":
    main()


