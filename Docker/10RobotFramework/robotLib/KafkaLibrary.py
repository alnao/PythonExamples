#pip install kafka-python
from kafka import KafkaProducer
from robot.api.deco import keyword

class KafkaLibrary:
    def __init__(self, bootstrap_servers='localhost:9092'):
        self.bootstrap_servers = bootstrap_servers
        self.producer = None

    def _get_producer(self, server=None):
        if server and server != self.bootstrap_servers:
            self.bootstrap_servers = server
            if self.producer:
                self.producer.close()
            self.producer = None
        
        if not self.producer:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: v.encode('utf-8')
            )
        return self.producer

    @keyword("Send Message")
    def send_message(self, topic, message, server=None):
        if server is None:
            server = self.bootstrap_servers
        
        producer = self._get_producer(server)
        producer.send(topic, message)
        producer.flush()