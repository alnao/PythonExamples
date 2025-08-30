import time

def hello(event, context):
    print("sto per dormire per 4 secondi");
    time.sleep(4)
    print("ho dormito 4 secondi");
    return "Dormito nel py-example2-timeout";
