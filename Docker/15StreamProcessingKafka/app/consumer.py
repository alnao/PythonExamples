import json
import time

from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

from .common import BOOTSTRAP_SERVERS, GROUP_ID, TOPIC


def wait_for_kafka(max_retries: int = 30, delay: int = 2) -> None:
    """Attende che Kafka sia disponibile prima di procedere."""
    for i in range(max_retries):
        try:
            consumer = KafkaConsumer(
                bootstrap_servers=BOOTSTRAP_SERVERS,
                api_version=(0, 10, 1),
            )
            consumer.close()
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
    
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        group_id=GROUP_ID,
        auto_offset_reset="earliest",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        enable_auto_commit=True,
    )

    print("Consumer started, waiting for messages...")
    for message in consumer:
        print(f"Consumed: {message.value}")


if __name__ == "__main__":
    main()


