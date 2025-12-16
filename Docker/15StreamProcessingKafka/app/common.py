import os


BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "demo-topic")
GROUP_ID = os.getenv("KAFKA_GROUP_ID", "demo-group")


