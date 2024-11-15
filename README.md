# Python Examples
Esempi Python by [AlNao.it](https://www.alnao.it)

## AWS
- Prerequisito: utenza AWS e installazione della AWS-CLI, vedere il [sito ufficiale](), per la configurazione eseguire comando `aws configure`.
- **CDK**: Per la libreria CDK, installare della libreria, vedere il [sito ufficiale](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html) eseguire il comando `npm install -g aws-cdk`. Per ogni progetto c'è un README dedicato:
  - 01 **bucketS3**: creazione di un bucket
  - 02 **EC2**: creazione di una istanza EC2
  - 03 **website S3**: creazione di una sito web esposto con S3
  - 04 **cloud front**: creazione di una distribuzione con CloudFront, vedere [repository aws-samples](https://github.com/aws-samples/deploy-cloudfront-in-china-with-cdk/blob/main/Python/lib/cloudfront_in_china_stack.py)
  - 05 **lambda function**: creazione di una funzione lambda function, vedere [repository aws-samples](https://github.com/aws-samples/aws-cdk-examples/tree/main/python/lambda-with-existing-s3-code)
  - 06 **event bridge**: creazione di una regola EventBridge, vedere [repository aws-samples](https://github.com/aws-samples/aws-cdk-examples/blob/main/python/api-eventbridge-lambda/api_eventbridge_lambda/api_eventbridge_lambda.py) 
  - 07 **step function**: creazione di una step function con due lambda, vedere [repository aws-samples](https://github.com/aws-samples/aws-cdk-examples/blob/main/python/stepfunctions/stepfunctions/stepfunctions_stack.py)
  - 08 **api gateway**: api gateway con esposizione di una risorsa REST
  - 09 **dynamo api crud**: creazione di una tabella dynamo con api gateway e lambda come crud 
  - 10 **lambda auth**: creazione di una API REST con lambda authorizer per la validazione di Token JWT
  - 13 **glue job**: creazione di un job glue per leggere un file e modificarne il contenuto
  - 15 **SQS**: creazione di una coda SQS, un API con un metodo producer e un metodo consumer
  - 16 **SNS**: creazione di un sistema SNS con una lambda che scoda le notifiche
  - 18 **EFS**: creazione di un disco EFS montato da una EC2 che espone un server apache
  - 20 **ASG** e **ALB**: creazione di un AutoScaling group e Application Load Balancer con EC2 che eseguono un webserver apache senza disco condiviso

- **ManagerTk**: *Applicazione* sviluppata con la libreria tkinter (menu, gestione finestre ed elenchi) per gestire i servizi AWS usando le librerie SDK
- **ManagerFlask**: *Applicazione* web sviluppata con Flask per gestire i servizi AWS usando le librerie SDK
  - **ManagerFlaskCloudWatch**: *Applicazione* web sviluppata con Flask per la gestione di CloudWatch Alarms & CloudWatch  
- **SDK**: Per la libreria SDK, l'installazione e la configurazione vedere il [sito ufficiale](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html) e il comando `pip install boto3`. Classi per la gestione dei servizi: profiles, SSM parameter, Bucket S3, Ec2, CloudFront, Lambda, Event bridge, Step function, Dynamo, RDS e tanti altri.
- **Services**
  - **CodeWhisperer**
    - 01 **basic**: semplice esempio usato come prima prova
  - **Glue**
    - 01 **console**: Semplice esempio creato da console manualmente che elabora un file csv con una struttura ben definita (numero,lettera,lungo,gruppo), filtra gli elementi che hanno gruppo = 'A' e salva un nuovo file con la stessa struttura. Non è possibile eseguirlo in locale.
  - **Polly**: text to speech, esempio preso dalla [documentazione ufficiale](https://docs.aws.amazon.com/it_it/polly/latest/dg/examples-python.html)

## Data Scientist
- **Pandas** e altre librerie per la manipolazione dati, see [khuyentran1401 website](https://khuyentran1401.github.io/Efficient_Python_tricks_and_tools_for_data_scientists/README.html)
- **Spark** vedere file README all'interno della cartella, progetti ispirati al corso [udemy.com/course/apache-spark](https://www.udemy.com/course/apache-spark-programming-in-python-for-beginners)

## Django
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
  - ArcadeLib: 
    - Snake see https://www.geeksforgeeks.org/python-arcade-player-movement/
    - Space see https://realpython.com/arcade-python-game-framework/
    - see https://api.arcade.academy/en/latest/examples/platform_tutorial/step_02.html
    - see https://realpython.com/arcade-python-game-framework/
  - Coffe: https://github.com/uxai/100daysofcode/blob/main/Day%2015/coffee_machine.py
  - Pong: https://api.arcade.academy/en/latest/examples/sections_demo_2.html#sections-demo-2
  - PyGame
    - see https://www.pygame.org/docs/
    - fly game: see https://realpython.com/pygame-a-primer/
    - asteroid: see https://realpython.com/asteroids-game-python/
  - Rogue Like tutorial see https://rogueliketutorials.com/tutorials/tcod/v2/part-1/
  - Tetris see https://api.arcade.academy/en/latest/examples/tetris.html#tetris
  - Vital_messages & shootout: https://www.youtube.com/watch?v=3kdM9wyglnw
  - TODO https://github.com/BlakeDalmas/Python
  - TODO Simple Platformer https://api.arcade.academy/en/latest/examples/platform_tutorial/index.html
  - TODO https://api.arcade.academy/en/latest/sample_games.html
  - TODO https://api.arcade.academy/en/stable/examples/procedural_caves_bsp.html
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

## pyinstaller
Come crare i file eseguibile da un python con **pyinstaller**, vedi [documentazione ufficiale](https://pyinstaller.org/en/stable/) e [video](https://www.youtube.com/watch?v=bqNvkAfTvIc). [Guida all'installazione](https://pyinstaller.org/en/v3.5/installation.html) e comando
```
pip install pyinstaller 
```

Per poi creare il file eseguibile dentro alla cartella dist del progetto:
```
pyinstaller file.py --onefile
pyinstaller ManagerTk.py --onefile  --hidden-import=Services --hidden-import=Services.services
pyinstaller --hidden-import=Services --hidden-import=Services.services  -F ManagerTk.py
```


# AlNao.it
Nessun contenuto in questo repository è stato creato con IA o automaticamente, tutto il codice è stato scritto con molta pazienza da Alberto Nao. Se il codice è stato preso da altri siti/progetti è sempre indicata la fonte. Per maggior informazioni visitare il sito [AlNao.it](https://www.alnao.it/).

## License
Public projects 
<a href="https://it.wikipedia.org/wiki/GNU_General_Public_License"  valign="middle"><img src="https://img.shields.io/badge/License-GNU-blue" style="height:22px;"  valign="middle"></a> 
*Free Software!*