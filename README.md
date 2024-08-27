# Python Examples
Esempi Python by [AlNao.it](https://www.alnao.it)

## AWS
Prerequisito l'installazione e la configurazione di AWS-CLI, vedere il [sito ufficiale]() e il comando `aws configure`.

Esempi di codice Python usando la AWS-CDK & la AWS-SDK:
- **CDK**: Per la libreria CDK, l'installazione e la configurazione vedere il [sito ufficiale](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html) e il comando `npm install -g aws-cdk`. Per ogni progetto c'è un README dedicato:
  - 01 **bucketS3**: creazione di un bucket
  - 02 **ec2**: creazione di una istanza EC2
  - 03 **website S3**: creazione di una sito web esposto con S3
  - 04 **cloud front**: creazione di una distribuzione con CloudFront, vedi [repository aws-samples](https://github.com/aws-samples/deploy-cloudfront-in-china-with-cdk/blob/main/Python/lib/cloudfront_in_china_stack.py)
  - 05 **lambda function**: creazione di una funzione lambda function, vedi [repository aws-samples](https://github.com/aws-samples/aws-cdk-examples/tree/main/python/lambda-with-existing-s3-code)
  - 06 **event bridge**: creazione di una regola EventBridge, vedi [repository aws-samples](https://github.com/aws-samples/aws-cdk-examples/blob/main/python/api-eventbridge-lambda/api_eventbridge_lambda/api_eventbridge_lambda.py) 
  - 07 **step function**: creazione di una step function con due lambda [repository aws-samples](https://github.com/aws-samples/aws-cdk-examples/blob/main/python/stepfunctions/stepfunctions/stepfunctions_stack.py)
- **CodeWhisperer**
  - 01 **basic**: semplice esempio usato come prima prova
- **Glue**
  - 01 **console**: Semplice esempio creato da console manualmente che elabora un file csv con una struttura ben definita (numero,lettera,lungo,gruppo), filtra gli elementi che hanno gruppo = 'A' e salva un nuovo file con la stessa struttura. Non è possibile eseguirlo in locale.
- **ManagerTk**: *Applicazione* sviluppata con la libreria tkinter (menu, gestione finestre ed elenchi)
- **ManagerFlask**: *Applicazione* web sviluppata con Flask
- **SDK**: Per la libreria SDK, l'installazione e la configurazione vedere il [sito ufficiale](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html) e il comando `pip install boto3`. Classi per la gestione dei servizi: profiles, SSM parameter, Bucket S3, Ec2, CloudFront, Lambda, Event bridge, Step function, Dynamo & RDS.
- **Services**
  - **Polly**: text to speech, esempio preso dalla [documentazione ufficiale](https://docs.aws.amazon.com/it_it/polly/latest/dg/examples-python.html)

## Data Scientist
Esempi di codice Python con 
- **Pandas** e altre librerie per la manipolazione dati, see [khuyentran1401 website](https://khuyentran1401.github.io/Efficient_Python_tricks_and_tools_for_data_scientists/README.html)
- **Spark**, see [udemy.com/course/apache-spark](https://www.udemy.com/course/apache-spark-programming-in-python-for-beginners)

## Django
Quattro esempi di progetti **Django** sviluppati:
- PythonDjango1example
- PythonDjango2news
- PythonDjango3forms
- PythonDjango4forms

## Docker
- 01 **simple Pandas**: see [run a python code on aws batch](https://medium.com/codex/run-a-python-code-on-aws-batch-part-1-creation-of-python-script-and-docker-container-1b01dc89eaed)
- 02 **Flask Login**: [esempio di docker](https://www.youtube.com/watch?v=ud_nq9lapF4) con dentro una piccola applicazione web creata con Flask e db (sqlite), 
- 03 **Api Persone NODB**: esempio di applicazione per l'esposizione di API, non previsto DB e non prevista concorrenza
- 04 **Flask login Ldap**: esempio di piccola applicazione Flask con la gestione delle credenziali tramite un server AD e protocollo LDAP
- 05 **Flask login Saml2-SSO**: esempio di piccola applicazione Flask con la gestione delle credenziali tramite un server AD e protocollo Saml2-SSO
- 06 **TraslatorSubtitle**: esempio di immagine per tradurre file subtitle in formato srt, see https://www.youtube.com/watch?v=-l7YocEQtA0

## From Others Sites
- Blockchain: esempi di implementazione dell'algoritmo "proof of work" con un unico nodo e un secondo esempio multi-nodo con metodo per la sincronia
- FaceDetector: https://www.youtube.com/watch?v=i3sLv1sus0I
- FastApi https://realpython.com/fastapi-python-web-apis/
- FlaskGeolocalNotes: https://www.youtube.com/watch?v=w-rti-5KHME
- FlaskLogin: https://www.youtube.com/watch?v=ud_nq9lapF4
- FlaskLoginGoogle: https://realpython.com/flask-google-login/
- Ia: https://www.youtube.com/watch?v=CkkjXTER2KE
- SimpleGames
  - Coffe: https://github.com/uxai/100daysofcode/blob/main/Day%2015/coffee_machine.py
  - PyGame01: see https://www.pygame.org/docs/
  - PyGame02 fly game: see https://realpython.com/pygame-a-primer/
  - PyGame03 asteroid:  see https://realpython.com/asteroids-game-python/
  - Rogue Like tutorial see https://rogueliketutorials.com/tutorials/tcod/v2/part-1/
  - Vital_messages & shootout: https://www.youtube.com/watch?v=3kdM9wyglnw
- TkinterExample:  https://www.youtube.com/watch?v=5qOnzF7RsNA (Tkinter e "Python Simplified")
- Youtube Downloader: https://www.youtube.com/watch?v=EMlM6QTzJo0 
- NotificationCron: https://www.youtube.com/watch?v=7ahUnBhdI5o
- Traslator: see https://huggingface.co/spaces/Mediocreatmybest/PipelineTranslator/blob/main/app.py

## Manage File
- Csv2fixedWidthFile: esempio di script py che prende un file csv e lo trasforma in un file txt posizionale
  - tracciato.csv necessario con i campi del file posizionale con le informazioni: nome, tipo, lunghezza, valore e descrizione
  - input.csv file di input coni campi 
  - l'ouput viene scritto in un file OUT.txt
- Marge2txtFile: esempio di script py che esegue marge di due file
  -  un file di testo txt (chiamato BAN) e un file csv (chiamato rapporti)
  -  genera un file di testotxt (chiamato OUT.txt) e un file csv di report con quali righe sono state modificate (OUT.log)
- Sftp_ssh: metodi per la gestione di un server sftp (invio e ricezione dati), esecuzione comando in remoto con ssh
- UnzipFile: esempio che usa "zipfile" di Py per estrarre il contenuto di un pacchetto zip
- UploadFileToRestAPI: esempio per l'invio di un file locale ad una API Rest 
- VideoConcat_ffmpeg: script per eseguire il concat di più video usando ffmpeg (solo su GNU Linux)

## Simple
- **gui**: esempi vari di librerie GUI per Python
- **mongo**: script per la gestione di una base dati NoSql Mongo
- **rabbitMq**: script la gestione di una coda RabbitMq
- classes.py: Esempio di classe Python
- conto1.py: Esercitazione classe ContoCorrente, inizializzatore con 3 parametri (nome titolare, numero conto e saldo) con tre attributi (nome, conto e saldo)
- conto2.py: Esercitazione classe ContoCorrente, prendere spunto dal conto1.py ma nascondere il saldo come proprietà semplice con una property ''privata'' , 
- conto3.py: Esercitazione classe Conto come padre di ContoCorrente, in conto ci devono essere nome e numero conto
- conto4.py: Esercitazione classe Gestore Conto corrente, crea metodo bonifico per prelevare da un conto e fare un deposito ad un altro
- exception.py: Esempi di exception in Python
- lambda.py: esempi di lambda in Python
- modules.py: Esempi di modulo in Python
- scriptWithModules.py: Eempi di script che importa un modulo (modules.py) in Python

## Creazione server
Vedere la [documentazione ufficiale](https://docs.python.org/es/3.10/library/http.server.html) o pagine di [esempio](https://ryanblunden.com/create-a-http-server-with-one-command-thanks-to-python-29fcfdcd240e?gi=45d07bd349a1).
Per lanciare il server, il comando è
```
python -m http.server 8080
```
e poi il server è pronto alla pagina `http://localhost:8080/`.


# AlNao.it
Nessun contenuto in questo repository è stato creato con IA o automaticamente, tutto il codice è stato scritto con molta pazienza da Alberto Nao. Se il codice è stato preso da altri siti/progetti è sempre indicata la fonte. Per maggior informazioni visitare il sito [AlNao.it](https://www.alnao.it/).

## License
Public projects 
<a href="https://it.wikipedia.org/wiki/GNU_General_Public_License"  valign="middle"><img src="https://img.shields.io/badge/License-GNU-blue" style="height:22px;"  valign="middle"></a> 
*Free Software!*