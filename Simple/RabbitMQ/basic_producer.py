import pika
import logging
#logging.basicConfig(level=logging.DEBUG)

print("Inizio producer, mi collego al RabbitMQ")
params = pika.ConnectionParameters( host="localhost", port="5672" ) #"localhost" se locale , check port
connection = pika.BlockingConnection(params)
channel = connection.channel()
channel.queue_declare ( queue="nomeCodaNelBroker" )
print("Connessione terminata, invio i messaggi")
for i in range(0,10000):
    message="Messaggio " +str(i)
    channel.basic_publish( exchange='', routing_key='nomeCodaNelBroker' , body = message )
    #exchange vuoto perchè default, routing_key ='wok
    print("Inviato %s",message)
connection.close()
print("Finito producer")