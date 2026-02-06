from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from typing import Any

from ..config import settings
from ..models import AnnotationIn


class QueueConsumer(ABC):
    @abstractmethod
    async def run(self) -> None:
        raise NotImplementedError


class KafkaConsumerWorker(QueueConsumer):
    def __init__(self, pipeline):
        self.pipeline = pipeline

    async def run(self) -> None:  # pragma: no cover - integration path
        from aiokafka import AIOKafkaConsumer

        consumer = AIOKafkaConsumer(
            settings.kafka_topic,
            bootstrap_servers=settings.kafka_bootstrap,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            enable_auto_commit=True,
        )
        await consumer.start()
        try:
            async for msg in consumer:
                payload = msg.value
                annotations = [AnnotationIn(**payload)] if isinstance(payload, dict) else []
                self.pipeline.ingest(annotations)
        finally:
            await consumer.stop()


class SQSConsumerWorker(QueueConsumer):
    def __init__(self, pipeline):
        self.pipeline = pipeline

    async def run(self) -> None:  # pragma: no cover - integration path
        import boto3

        if not settings.sqs_queue_url:
            raise ValueError("sqs_queue_url not set")
        client = boto3.client("sqs", region_name=settings.aws_region)
        while True:
            resp = client.receive_message(
                QueueUrl=settings.sqs_queue_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=20,
            )
            messages = resp.get("Messages", [])
            if not messages:
                await asyncio.sleep(1)
                continue
            entries: list[Any] = []
            for m in messages:
                body = json.loads(m["Body"])
                if isinstance(body, dict):
                    entries.append(body)
            if entries:
                self.pipeline.ingest([AnnotationIn(**e) for e in entries])
            client.delete_message_batch(
                QueueUrl=settings.sqs_queue_url,
                Entries=[{"Id": m["MessageId"], "ReceiptHandle": m["ReceiptHandle"]} for m in messages],
            )


def build_consumer(pipeline) -> QueueConsumer:
    backend = settings.queue_backend.lower()
    if backend == "kafka":
        return KafkaConsumerWorker(pipeline)
    if backend == "sqs":
        return SQSConsumerWorker(pipeline)
    raise ValueError(f"Unsupported queue backend: {backend}")
