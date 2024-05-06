# Python Examples
Esempi by [AlNao](https://www.alnao.it)

## AWS CDK
Esempio di codice Python usando la AWS-CDK boto3. Per l'installazione e la configurazione vedere il [sito ufficiale](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html) (`npm install -g aws-cdk`).

Lista degli esempi disponibili:
- Cdk01 **bucket S3**: primo rilascio usando i comandi base CDK per la creazione di un bucket tramite libreria AWS-CDK


## AWS Code Whisperer
Esempi di codice Python generati con AWS CodeWhisperer


## AWS Glue
Esempi di codice Python con Spark e Pandas per la manipolazione dati con il servizio AWS Glue
- 01 **console**: Semplice esempio creato da console manualmente che elabora un file csv con una struttura ben definita (numero,lettera,lungo,gruppo), filtra gli elementi che hanno gruppo = 'A' e salva un nuovo file con la stessa struttura. Non è possibile eseguirlo in locale.

## Blockchain
Esempio di scipt per l'implementazione dell'algoritmo "proof of work" con un unico nodo e un secondo esempio multi-nodo con metodo per la sincronia


## Data Scientists
Esempi di codice Python con Pandas e altre librerie per la manipolazione dati.
See https://khuyentran1401.github.io/Efficient_Python_tricks_and_tools_for_data_scientists/README.html


## Django
Tre esempi di progetti Django sviluppati dal corso 
- PythonDjango1example
- PythonDjango2news
- PythonDjango3forms


## Docker
- 01 **simple Pandas**, see https://medium.com/codex/run-a-python-code-on-aws-batch-part-1-creation-of-python-script-and-docker-container-1b01dc89eaed
- 02 **Flask Login**: esempio di docker con dentro una piccola applicazione web creata con Flask e db (sqlite), see https://www.youtube.com/watch?v=ud_nq9lapF4
- 03 **Api Persone NODB**: esempio di applicazione per l'esposizione di API, non previsto DB e non prevista concorrenza
- 04 **Flask login Ldap**: esempio di piccola applicazione Flask che si collega ad un server AD tramite protocollo LDAP

## From Others Sites
- Blockchain (python simple example of blockchain with multiple nodes)
- ChatGPT
- FaceDetector: https://www.youtube.com/watch?v=i3sLv1sus0I
- FlaskGeolocalNotes: https://www.youtube.com/watch?v=w-rti-5KHME
- FlaskLogin: https://www.youtube.com/watch?v=ud_nq9lapF4
- TkinterExample:  https://www.youtube.com/watch?v=5qOnzF7RsNA (Tkinter e "Python Simplified")
- Youtube Downloader: https://www.youtube.com/watch?v=EMlM6QTzJo0 
- NotificationCron: https://www.youtube.com/watch?v=7ahUnBhdI5o
- SimpleIa: https://www.youtube.com/watch?v=CkkjXTER2KE
- SimpleGames
  - Coffe: https://github.com/uxai/100daysofcode/blob/main/Day%2015/coffee_machine.py
  - Vital_messages & shootout: https://www.youtube.com/watch?v=3kdM9wyglnw
  - Rogue Like tutorial see https://rogueliketutorials.com/tutorials/tcod/v2/part-1/

## Manage File
- Marge2txtFile: Esempio di script py che esegue marge di due file
  -  un file di testo txt (chiamato BAN) e un file csv (chiamato rapporti)
  -  genera un file di testotxt (chiamato OUT.txt) e un file csv di report con quali righe sono state modificate (OUT.log)
- Csv2fixedWidthFile: Esempio di script py che prende un file csv e lo trasforma in un file txt posizionale
  - tracciato.csv necessario con i campi del file posizionale con le informazioni: nome, tipo, lunghezza, valore e descrizione
  - input.csv file di input coni campi 
  - l'ouput viene scritto in un file OUT.txt
- UnzipFile: Semplice esempio che usa "zipfile" di Py per estrarre il contenuto di un pacchetto zip

## Simple
- **mongo**: script per la gestione di una base dati NoSql Mongo
- **rabbitMq**: script la gestione di una coda RabbitMq
- conto1.py: Esercitazione classe ContoCorrente, inizializzatore con 3 parametri (nome titolare, numero conto e saldo) con tre attributi (nome, conto e saldo)
- conto2.py: Esercitazione classe ContoCorrente, prendere spunto dal conto1.py ma nascondere il saldo come proprietà semplice con una property ''privata'' , 
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