#!/usr/bin/env python3
import json
import logging
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any
import uuid
import boto3
import requests
from kafka import KafkaConsumer
from botocore.exceptions import ClientError
from threading import Thread
import signal
import sys
import os

# Configurazione base del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ConsumerConfig:
    """Configurazione del consumer"""
    kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    kafka_topic: str = os.getenv("KAFKA_TOPIC", "test.alberto")
    kafka_group_id: str = os.getenv("KAFKA_GROUP_ID", "alberto-consumer-group")
    dynamodb_endpoint: str = os.getenv("DYNAMODB_ENDPOINT", "http://localhost:8000")
    dynamodb_table: str = os.getenv("DYNAMODB_TABLE", "alberto-dy2")
    dynamodb_region: str = os.getenv("DYNAMODB_REGION", "us-east-1")
    api_endpoint: Optional[str] = os.getenv("API_ENDPOINT")  # Può essere None
    max_workers: int = int(os.getenv("MAX_WORKERS", "1"))
    #consumer_timeout: Optional[int] = os.getenv("CONSUMER_TIMEOUT") and int(os.getenv("CONSUMER_TIMEOUT"))
    #api_timeout: int = int(os.getenv("API_TIMEOUT", "5"))
    consumer_timeout_ms: Optional[int] = None


class MessageProcessor:
    def __init__(self, config: ConsumerConfig):
        self.config = config
        self.consumer_id = str(uuid.uuid4())[:8]

        # Setup DynamoDB con UNSIGNED signature per ambiente locale
        self.dynamodb = boto3.resource(
            'dynamodb',
            endpoint_url=self.config.dynamodb_endpoint,
            region_name=self.config.dynamodb_region,
            aws_access_key_id='fakeAccessKey',
            aws_secret_access_key='fakeSecretKey',
#            config=boto3.session.Config(signature_version='unsigned')
        )
        self.table = self.dynamodb.Table(self.config.dynamodb_table)

        # Setup HTTP session
        self.session = requests.Session()
        self.session.timeout = self.config.max_workers

    def call_api(self, message_data: Dict) -> Optional[Dict]:
        """Chiama una mock API (es. http://mockbin.org/echo/post/json)"""
        if not self.config.api_endpoint:
            logger.debug(f"Mock API chiamata per ID {message_data.get('id', 'unknown')}")
            time.sleep(0.1)
            return {
                "status": "processed",
                "timestamp": time.time(),
                "api_response": "mock_success"
            }

        try:
            response = self.session.post(
                self.config.api_endpoint,
                json=message_data,
                timeout=5
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Errore API call: {e}")
            return None

    def save_to_dynamo(self, message_data: Dict, api_result: Optional[Dict]) -> bool:
        """Salva i dati in DynamoDB"""
        item = {
            'id': message_data.get('id', str(uuid.uuid4())),
            'original_message': json.dumps(message_data),
            'consumer_id': self.consumer_id,
            'processed_at': int(time.time()),
        }

        if api_result:
            item['api_result'] = json.dumps(api_result)
            item['api_status'] = api_result.get('status', 'unknown')

        try:
            self.table.put_item(Item=item)
            logger.info(f"Messaggio {item['id']} salvato in DynamoDB")
            return True
        except ClientError as e:
            logger.error(f"Errore DynamoDB: {e.response['Error']['Message']}")
            return False
        except Exception as e:
            logger.error(f"Errore generico nel salvataggio: {e}")
            return False

    def process_message(self, message_value: bytes) -> bool:
        """Processa un singolo messaggio"""
        try:
            message_data = json.loads(message_value.decode('utf-8'))
            logger.info(f"Processando messaggio {message_data.get('id', 'unknown')}")

            api_result = self.call_api(message_data)
            success = self.save_to_dynamo(message_data, api_result)

            if success:
                logger.info(f"Messaggio elaborato con successo")
            else:
                logger.warning(f"Elaborazione fallita")

            return success
        except Exception as e:
            logger.error(f"Errore durante l'elaborazione del messaggio: {e}")
            return False

class KafkaSimpleConsumer:
    def __init__(self, config: ConsumerConfig):
        self.config = config
        self.running = True
        self.processor = MessageProcessor(config)
        self.consumer = None

    def _create_consumer(self) -> KafkaConsumer:
        consumer_kwargs = {
            'bootstrap_servers': self.config.kafka_bootstrap_servers,
            'group_id': self.config.kafka_group_id,
            'auto_offset_reset': 'latest',
            'enable_auto_commit': True,
            'value_deserializer': lambda x: x
        }
        if self.config.consumer_timeout_ms is not None:
            consumer_kwargs['consumer_timeout_ms'] = self.config.consumer_timeout_ms
        try:
            consumer = KafkaConsumer(self.config.kafka_topic, **consumer_kwargs)
        except Exception as err:
            logger.error(f"Errore nella creazione del consumer: {err}")
            raise Exception(f"{err}")
        logger.info(f"Consumer avviato per topic '{self.config.kafka_topic}'")
        return consumer

    def start(self):
        self.consumer = self._create_consumer()

        for message in self.consumer:
            if not self.running:
                break
            logger.debug(f"Ricevuto messaggio da partition {message.partition}, offset {message.offset}")
            self.processor.process_message(message.value)

    def stop(self):
        self.running = False
        if self.consumer:
            self.consumer.close()
        logger.info("Consumer fermato")

def main():
    config = ConsumerConfig(
#        kafka_bootstrap_servers='localhost:9092',
#        kafka_topic='test.alberto',
#        dynamodb_endpoint='http://localhost:8000',
#        dynamodb_table='alberto-dy2',
#        api_endpoint=None  # Usa mock API se None
    )

    consumer = KafkaSimpleConsumer(config)

    def signal_handler(sig, frame):
        logger.info("Ricevuto segnale di interruzione, termino...")
        consumer.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        logger.info("Avvio Kafka Consumer v2...")
        consumer.start()
    except KeyboardInterrupt:
        pass
    finally:
        consumer.stop()

if __name__ == "__main__":
    main()