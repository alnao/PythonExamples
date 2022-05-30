import pika
import logging
#logging.basicConfig(level=logging.DEBUG)

#metodo che elabora elemento dalla coda
def funzione_callback(channel, method, properties, body):
    print("Body ricevuto: %s",body)

#consumer code:
print("Inizio consumer, mi collego al RabbitMQ")
params = pika.ConnectionParameters( host="localhost", port="5672" ) #"localhost" se locale , check port
connection = pika.BlockingConnection(params)
channel = connection.channel()
channel.queue_declare ( queue="nomeCodaNelBroker" )
print("Connessione terminata, ricevo i messaggi")
channel.basic_consume( on_message_callback=funzione_callback, queue="nomeCodaNelBroker" , auto_ack=True )
#no_ack=True significa che il metodo NON ritorna una conferma di lettura ed elaborazione
channel.start_consuming() #si ferma qui ed elabora finchè