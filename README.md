# PythonExamples
Python Examples by AlNao


## Mongo
- esempi per iteragire con una base dati Mongo che deve essere installata e disponibile sulla porta di default , la libreria si installa con il comando
```
$ pip install pymongo
```
- to run
    ```
    $ python3 example1create.py
    $ python3 example2access.py
    $ python3 example3edit.py

    ```

## RabbitMQ

### BASIC example
- esempio basic di script per scrivere una stringa su una coda RabbitMQ e leggerla. Prerequisito aver installato pika con pip3 e aver installato RabbitMQ nel proprio sistema (la porta potrebbe essere diversa dalla dell'esempio a seconda del sistema operativo)


- to run
    per avviare il producer 
    ```
    $ python3 basic_producer.py
    ```
    per lanciare uno o più consumer (su console differenti dal producer)
    ```
    python3 basic_consumer.py
    ```
- notare che quando si avvia il producer viene consumata tanta CPU perchè ci sono i print, ogni consumer riceve un terzo perchè RabbitMQ configurato di default con RoundRobin che divide equamente: il promo messaggio al primo, il secondo al secondo, il terzo a terzo e il quarto al primo se sono 3 consumer.


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

### UnzipFile
- semplice esempio che usa "zipfile" di Py per estrarre il contenuto di un pacchetto zip


## FromOthersSite
- Coffe.py

  from https://github.com/uxai/100daysofcode/blob/main/Day%2015/coffee_machine.py

  to run
  ```
  $ python3 FromOthersSite/Coffe.py 
  ```

## TkinterExample
Esempi semplici con la libreria Tkinter, prendendo spunto dal canale youtube "Python Simplified"


### example1
- semplice finestra con immagine, un testo e un bottone che esegue una print

- to run 
  ```
  $ python3 TkinterExample/example1.py 
  ```

## PythonDjango
Tre esempi di progetti Django sviluppati dal corso 
- PythonDjango1example
- PythonDjango2news
- PythonDjango3forms


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
