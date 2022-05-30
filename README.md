# PythonExamples
Python Examples by AlNao

## RabbitMQ

### BASIC example
- esempio basic di script per scrivere una stringa su una coda RabbitMQ e leggerla. Prerequisito aver installato pika con pip3 e aver installato RabbitMQ nel proprio sistema (potrebbe essere diversa dalla 5672)


per avviare il producer 
```
$ python3 basic_producer.py
```
per lanciare uno o più consumer (su console differenti dal producer)
```
python3 basic_consumer.py
```
notare che si avvia si produce tanta CPU perchè ci sono i print, ogni consumer riceve un terzo perchè RabbitMQ configurato di default con RoundRobin che divide equamente: il promo messaggio al primo, il secondo al secondo


## ManagerFile

### Marge2txtFile
- esempio di script py che esegue marge di due file
	
    un file di testo txt (chiamato BAN) e un file csv (chiamato rapporti)
	
    genera un file di testotxt (chiamato OUT.txt) e un file csv di report con quali righe sono state modificate (OUT.log)

### Csv2fixedWidthFile
- esempio di script py che prende un file csv e lo trasforma in un file txt posizionale

    tracciato.csv necessario con i campi del file posizionale con le informazioni: nome, tipo, lunghezza, valore e descrizione

    input.csv file di input coni campi 

    l'ouput viene scritto in un file OUT.txt


## FromOthersSite
- Coffe.py

  from https://github.com/uxai/100daysofcode/blob/main/Day%2015/coffee_machine.py

  to run
  ```
  $ python3 FromOthersSite/Coffe.py 
  ```



## Simple

### conto1.py
- esercitazione classe ContoCorrente 
	
    inizializzatore con 3 parametri (nome titolare, numero conto e saldo) 
	
    tre attributi (nome, conto e saldo)
	
    metodo preleva con un parametro importo
	
    metodo deposita con un parametro importo
	
    metodo descrizione senza paraemtri e visualizza : nome, conto e saldo
	
    crea folder, crea conto1.py
	
    codice per testare la classe: 2 conti

- to run 
  ```
  $ python3 Simple/conto1.py 
  ```

### conto2.py
- esercitazione classe ContoCorrente 
	
    prendere spunto dal conto1.py ma nascondere il saldo come proprietà semplice
    
    una property ''privata'' , modificando il saldo in __saldo
    
    nascondere attributo saldo, getter e setter

- to run 
  ```
  $ python3 Simple/conto2.py 
  ```


### conto3.py
- esercitazione classe Conto come padre di ContoCorrente
	
    in conto ci devono essere nome e numero conto
    
- to run 
  ```
  $ python3 Simple/conto3.py 
  ```

### conto4.py
- esercitazione classe Gestore Conto corrente

    crea metodo bonifico per prelevare da un conto e fare un deposito ad un altro

- to run 
  ```
  $ python3 Simple/conto4.py 
  ```
### exception.py
- esempi di exception in Py
- to run 
  ```
  $ python3 Simple/exception.py 
  ```

### modules.py
- esempi di modulo in Py
- to run 
  ```
  $ python3 Simple/modules.py 
  ```

### scriptWithModules.py
- esempi di script che importa un modulo (modules.py) in Py
- to run 
  ```
  $ python3 Simple/scriptWithModules.py 
  ```
