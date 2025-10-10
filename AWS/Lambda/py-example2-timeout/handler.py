import time

def hello(event, context):
    print("sto per dormire per 5 secondi");
    time.sleep(5)
    print("ho dormito 5 secondi");
    return "Dormito nel py-example2-timeout per 5 secondi";
