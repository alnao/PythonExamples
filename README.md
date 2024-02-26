
<p align="center">
    <a href="https://www.alnao.it/">
      <img src="https://img.shields.io/badge/alnao-.it-blue?logo=amazoncloudwatch&logoColor=A6C9E2" height="50px;"  />
    </a>
</p>

# PythonExamples
PythonExamples Examples by [AlNao](https://www.alnao.it)

## AWS CDK
Esempio di codice Python usando la AWS-CDK boto3
- 01 first deploy: primo rilascio usando i comandi base CDK per la creazione di un bucket tramite libreria CDK


## AWS Code Whisperer
Esempi di codice Python generati con AWS CodeWhisperer

## AWS Glue
Esempi di codice Python con Spark e Pandas per la manipolazione dati con il servizio AWS Glue
- 01console: Semplice esempio creato da console manualmente che elabora un file csv con una struttura ben definita (numero,lettera,lungo,gruppo), filtra gli elementi che hanno gruppo = 'A' e salva un nuovo file con la stessa struttura. Non è possibile eseguirlo in locale.


## Data Scientists
Esempi di codice Python con Pandas e altre librerie per la manipolazione dati.
See https://khuyentran1401.github.io/Efficient_Python_tricks_and_tools_for_data_scientists/README.html
- "01collections_itertools" esempi di metodi per la manipolazione di collezioni e uso di itertools

## Docker
- 01 simple Pandas see https://medium.com/codex/run-a-python-code-on-aws-batch-part-1-creation-of-python-script-and-docker-container-1b01dc89eaed

## From Others Sites
- ChatGPT
- FaceDetector see https://www.youtube.com/watch?v=i3sLv1sus0I
- FlaskGeolocalNotes  see https://www.youtube.com/watch?v=w-rti-5KHME
- TkinterExample see  https://www.youtube.com/watch?v=5qOnzF7RsNA (Tkinter e "Python Simplified")
- Youtube Downloader see https://www.youtube.com/watch?v=EMlM6QTzJo0 
- Coffe.py see https://github.com/uxai/100daysofcode/blob/main/Day%2015/coffee_machine.py
- NotificationCron.py see https://www.youtube.com/watch?v=7ahUnBhdI5o
- SimpleIa.py see https://www.youtube.com/watch?v=CkkjXTER2KE

## Manage File
- Marge2txtFile: Esempio di script py che esegue marge di due file
  -  un file di testo txt (chiamato BAN) e un file csv (chiamato rapporti)
  -  genera un file di testotxt (chiamato OUT.txt) e un file csv di report con quali righe sono state modificate (OUT.log)
- Csv2fixedWidthFile: Esempio di script py che prende un file csv e lo trasforma in un file txt posizionale
  - tracciato.csv necessario con i campi del file posizionale con le informazioni: nome, tipo, lunghezza, valore e descrizione
  - input.csv file di input coni campi 
  - l'ouput viene scritto in un file OUT.txt
- UnzipFile: Semplice esempio che usa "zipfile" di Py per estrarre il contenuto di un pacchetto zip

## Mongo
Esempi per iteragire con una base dati Mongo che deve essere installata e disponibile sulla porta di default , la libreria si installa con il comando

```
$ pip install pymongo
```

To run
```
$ python3 example1create.py
$ python3 example2access.py
$ python3 example3edit.py
```

## PythonDjango
Tre esempi di progetti Django sviluppati dal corso 
- PythonDjango1example
- PythonDjango2news
- PythonDjango3forms

## RabbitMq
Esempio basic di script per scrivere una stringa su una coda RabbitMQ e leggerla. Prerequisito aver installato pika con pip3 e aver installato RabbitMQ nel proprio sistema (la porta potrebbe essere diversa dalla dell'esempio a seconda del sistema operativo)


To run
    per avviare il producer 
    ```
    $ python3 basic_producer.py
    ```
    per lanciare uno o più consumer (su console differenti dal producer)
    ```
    python3 basic_consumer.py
    ```
Notare che quando si avvia il producer viene consumata tanta CPU perchè ci sono i print, ogni consumer riceve un terzo perchè RabbitMQ configurato di default con RoundRobin che divide equamente: il promo messaggio al primo, il secondo al secondo, il terzo a terzo e il quarto al primo se sono 3 consumer.

## Simple
- conto1.py: Esercitazione classe ContoCorrente, inizializzatore con 3 parametri (nome titolare, numero conto e saldo) con tre attributi (nome, conto e saldo)
	- metodo preleva con un parametro importo
	- metodo deposita con un parametro importo
	- metodo descrizione senza paraemtri e visualizza : nome, conto e saldo
- conto2.py: Esercitazione classe ContoCorrente, prendere spunto dal conto1.py ma nascondere il saldo come proprietà semplice con una property ''privata'' , modificando il saldo in __saldo e nascondere attributo saldo, getter e setter
- conto3.py: Esercitazione classe Conto come padre di ContoCorrente, in conto ci devono essere nome e numero conto
- conto4.py: Esercitazione classe Gestore Conto corrente, crea metodo bonifico per prelevare da un conto e fare un deposito ad un altro
- exception.py: Esempi di exception in Py
- modules.py: Esempi di modulo in Py
- scriptWithModules.py: Eempi di script che importa un modulo (modules.py) in Py


# AlNao.it
Nessun contenuto in questo repository è stato creato con IA o automaticamente, tutto il codice è stato scritto con molta pazienza da Alberto Nao. Se il codice è stato preso da altri siti/progetti è sempre indicata la fonte. Per maggior informazioni visitare il sito [alnao.it](https://www.alnao.it/).

## License
Public projects 
<a href="https://it.wikipedia.org/wiki/GNU_General_Public_License"  valign="middle"><img src="https://img.shields.io/badge/License-GNU-blue" style="height:22px;"  valign="middle"></a> 
*Free Software!*