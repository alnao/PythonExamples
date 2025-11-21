# Python Examples ✨

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.8+" height=60/>
  <img src="https://img.shields.io/badge/AWS-Cloud-orange?style=for-the-badge&logo=amazon-aws&logoColor=white" alt="AWS" height=60/>
  <!--<img src="https://img.shields.io/badge/Django-Framework-green?style=for-the-badge&logo=django&logoColor=white" alt="Django">-->
  <img src="https://img.shields.io/badge/Docker-Container-blue?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" height=60/>
  <!--<img src="https://img.shields.io/badge/Flask-Web-lightgrey?style=for-the-badge&logo=flask&logoColor=white" alt="Flask" height=60/>-->
</p>

## ✨ Panoramica

Benvenuti nella collezione di esempi Python by [AlNao.it](https://www.alnao.it)! 
- **☁️ Cloud Computing con AWS ed Azure**: Esempi completi per CDK-SDK per i servizi Cloud di AWS e di Azure
- **🌐 Sviluppo Web**: Applicazioni Flask, Django, API REST e interfacce web moderne
- **🐳 Containerizzazione**: Progetti Docker e Kubernetes pronti per la produzione
- **📊 Data Science**: Manipolazione dati con Pandas, Spark e tecniche di analisi avanzate
- **🎮 Applicazioni GUI**: Interfacce desktop con Tkinter e altre librerie grafiche
- **🎯 Progetti Pratici**: Dall'automazione di file alla gestione di database NoSQL



## AWS
- Per eseguire correttamente gli esempi relativi ai servizi AWS, è necessario avere:
  - Account AWS attivo e avere installata la [AWS Command Line Interface](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).
  - Credenziali configurate con il comando `aws configure` (con Access Key, Secret Key, regione)
  - Permessi adeguati: L’utente AWS deve avere i permessi necessari per i servizi utilizzati (S3, Lambda, EC2, DynamoDB, ecc.).
  - Tool e librerie: Python 3.8+, pip e boto3, Node.js e npm, Docker
- **Bedrock**: un sistema **RAG (Retrieval-Augmented Generation)** completo utilizzando i servizi AWS, con particolare focus su **Amazon Bedrock** per l'intelligenza artificiale. Il sistema permette di caricare documenti, indicizzarli semanticamente e interrogarli in linguaggio naturale, combinando la potenza dei modelli di embedding e chat di AWS Bedrock.
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
- **Glue**
  - 01 **console**: Semplice esempio creato da console manualmente che elabora un file csv con una struttura ben definita.
  - 02 **sqlServer** e **example03sqlServerWithRunSql**: Esempio creato per importare in database RDS SqlServer il contenuto di un file CSV (funziona anche con file di grandi dimensioni a differenze di una lambda che andrebbe in errore per timeout)
- **Lambda**: vari esempi di lambda scritte in python con, vedere il README nella cartella e il [sito ufficiale di serverless](https://www.serverless.com/). 
- **Managers**
  - **ManagerFlask**: *Applicazione web* sviluppata con Flask per gestire i servizi AWS usando le librerie SDK
  - **ManagerFlaskCloudWatch**: *Applicazione web* sviluppata con Flask per la gestione di CloudWatch Alarms & CloudWatch  
  - **ManagerTk**: *Applicazione* sviluppata con la libreria tkinter (menu, gestione finestre ed elenchi) per gestire i servizi AWS usando le librerie SDK/boto
  - **PanoramicResources**: semplice *Dashboard* per visualizzare delle risorse di un account AWS
- **Polly**: text to speech, esempio preso dalla [documentazione ufficiale](https://docs.aws.amazon.com/it_it/polly/latest/dg/examples-python.html), funzionante anche con la lingua italiana selezionando la voce `Bianca (Famale, Italian)`. Per eseguirlo basta lanciare `python server.py e` e poi procedere alla pagina `http://localhost:8000/index.html` che permette di eseguire.
  - **Amazon Polly**: è un servizio AWS specificamente dedicato alla sintesi vocale, ovvero alla generazione di audio (voce) a partire da testo. Polly non genera immagini né video a partire da testo. Polly può essere usato per generare tracce audio da inserire in video o slideshow, ma la generazione di immagini/video rimane esterna.
  - Soluzioni di terze parti: Puoi comunque integrare servizi esterni (come Runway, Pika, Synthesia, ecc.) sulle infrastrutture AWS, ma non sono prodotti AWS nativi. 
  - Amazon Rekognition: È un servizio per l’analisi di immagini e video (riconoscimento facciale, oggetti, moderazione), ma non genera contenuti multimediali.
- **SDK**: Per la libreria SDK, l'installazione e la configurazione vedere il [sito ufficiale](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html) e il comando `pip install boto3`. Classi per la gestione dei servizi: profiles, SSM parameter, Bucket S3, Ec2, CloudFront, Lambda, Event bridge, Step function, Dynamo, RDS e tanti altri.
  

## Azure
- **Managers**
  - **PanoramicResources**: semplice *Dashboard* per visualizzare delle risorse di un account Azure


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
- 03 **Api Persone NODB**: applicazione per l'esposizione di API, non previsto DB e non previsto sistema di concorrenza: *al riavvio si perde tutto*
- 04 **Flask login Ldap**: piccola applicazione Flask con la gestione delle credenziali tramite un server AD e protocollo LDAP
- 05 **Flask login Saml2-SSO**: piccola applicazione Flask con la gestione delle credenziali tramite un server AD e protocollo Saml2-SSO
- 06 **TraslatorSubtitle**: applicazione per tradurre file subtitle in formato srt, see [video](https://www.youtube.com/watch?v=-l7YocEQtA0)
- 07 **DockerCompose API**: applicazione con api-rest che legge e scrive dati su un database, app e database sono creati assieme con un docker-compose
- 08 **Crud MySql Minikubernetes**: applicazione con api-rest che legge e scrive dati su database mysql, creati con Kubernetes *funzionante* su Minikube
- 09 **AWS Dynamo**: applicazione che crea una tabella dynamo, un CRUD con fast-api e un piccolo frontend per visualizzare i dati
- 10 **Robot Framework**: applicazione che esegue un test-unit con RobotFramework di una *bellissima* infrastruttura con DynamoDb, Kafka, consumer e un frontend.
- 11 **llamaAIRaspberry3**: immagine per eseguire una IA con motore **Llama** in un docker, può essere eseguita su PC *o su Rasbperry3b*
- 12 **KubernetesScaling**: immagine per eseguire lo scaling con kubernetes utilizzando la funzionalità **Horizontal Pod Autoscalers** di K8S
  - l'immagine permette di mandare la CPU a valori alti con chiamate post
  - sotto-cartella con un esempio *funzionante* con **Prometheus** che utilizza una custum-metrics "numero task" e **Grafana** per il monitoraggio
  - sotto-cartella con tre esempi *funzionanti* con **CRD** e librerie *operator* per la gestione dello scaling.


## From Others Sites
- **Blockchain**: esempi di implementazione dell'algoritmo "proof of work" con un unico nodo e un secondo esempio multi-nodo con metodo per la sincronia
- **FaceDetector**: https://www.youtube.com/watch?v=i3sLv1sus0I
- **FastApi**: https://realpython.com/fastapi-python-web-apis/
- **FlaskGeolocalNotes**: https://www.youtube.com/watch?v=w-rti-5KHME
- **FlaskLogin**: https://www.youtube.com/watch?v=ud_nq9lapF4
- **FlaskLoginGoogle**: https://realpython.com/flask-google-login/
- **IA**: [How To Build A Chat Bot That Learns From The User In Python Tutorial](https://www.youtube.com/watch?v=CkkjXTER2KE)
- **IA_LargeLanguageModel** libro [Build a Large Language Model (From Scratch)" by Sebastian Raschka](https://github.com/rasbt/LLMs-from-scratch)
- **PlaywrightWebScraping**: site downloader, download all PDF, jump captcha with proxy [Web Scraping with Playwright + CAPTCHA Bypass For Beginners](https://www.youtube.com/watch?v=RGR5Xj0Qqfs)
- SimpleGames
  - **ArcadeLib**: 
    - Snake see https://www.geeksforgeeks.org/python-arcade-player-movement/
    - Space see https://realpython.com/arcade-python-game-framework/
    - see https://api.arcade.academy/en/latest/examples/platform_tutorial/step_02.html
    - see https://realpython.com/arcade-python-game-framework/
  - **Coffe**: https://github.com/uxai/100daysofcode/blob/main/Day%2015/coffee_machine.py
  - **Pong**: https://api.arcade.academy/en/latest/examples/sections_demo_2.html#sections-demo-2
  - **PyGame**
    - see https://www.pygame.org/docs/
    - fly game: see https://realpython.com/pygame-a-primer/
    - asteroid: see https://realpython.com/asteroids-game-python/
  - **Rogue Like**: tutorial see https://rogueliketutorials.com/tutorials/tcod/v2/part-1/
  - **Tetris**: see https://api.arcade.academy/en/latest/examples/tetris.html#tetris
  - **Vital_messages** & shootout: https://www.youtube.com/watch?v=3kdM9wyglnw
  - TODO https://github.com/BlakeDalmas/Python
  - TODO Simple Platformer https://api.arcade.academy/en/latest/examples/platform_tutorial/index.html
  - TODO https://api.arcade.academy/en/latest/sample_games.html
  - TODO https://api.arcade.academy/en/stable/examples/procedural_caves_bsp.html
- **TkinterExample**:  https://www.youtube.com/watch?v=5qOnzF7RsNA (Tkinter e "Python Simplified")
- **Youtube Downloader**: 
  - pytube.py dal https://www.youtube.com/watch?v=EMlM6QTzJo0 
  - main.py versione con flask
- **NotificationCron**: https://www.youtube.com/watch?v=7ahUnBhdI5o
- **Traslator**: see https://huggingface.co/spaces/Mediocreatmybest/PipelineTranslator/blob/main/app.py


## Manage File
- **CheckASCII**: script che verifica se in un file di testo ci sono carateri non AsciiUtf8
- **Csv2fixedWidthFile**: esempio di script py che prende un file csv e lo trasforma in un file txt posizionale
  - tracciato.csv necessario con i campi del file posizionale con le informazioni: nome, tipo, lunghezza, valore e descrizione
  - input.csv file di input coni campi 
  - l'ouput viene scritto in un file OUT.txt
- **Marge2txtFile**: esempio di script py che esegue marge di due file
  -  un file di testo txt (chiamato BAN) e un file csv (chiamato rapporti)
  -  genera un file di testotxt (chiamato OUT.txt) e un file csv di report con quali righe sono state modificate (OUT.log)
- **Sftp & ssh**: metodi per la gestione di un server sftp (invio e ricezione dati), esecuzione comando in remoto con ssh
- **UnzipFile**: esempio che usa "zipfile" di Py per estrarre il contenuto di un pacchetto zip
- **UploadFileToRestAPI**: esempio per l'invio di un file locale ad una API Rest 
- **VideoConcat ffmpeg**: script per eseguire il concat di più video usando ffmpeg (solo su GNU Linux)


## RobotFramework
- 01 Simple: robot che esegue test sulla login su una applicazioni di esempio
- 02 Database: robot che esegue query CRUD su un Database Mysql


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


## Appunti vari
In questa sezione appunti vari presi nel tempo
- corso base base https://www.youtube.com/watch?v=XHzDHJ-BgvU
- main # https://www.youtube.com/watch?v=NB5LGzmSiCs
	```
  if __name__ == '__main__':
		print("SI")
  ```
- main e recuperare un file dalla stessa cartella dove è presente il file main
  ```
  import os
  if __name__ == '__main__':
    # Ottiene il percorso della directory dove si trova lo script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'file.txt')
  ```
- Tipizzare e annotation https://www.youtube.com/watch?v=Y9fT4HVdCuQ
  ```
  def get_data() -> dict[str,int]:
	return {'bob':1,'james':2}
  ```
- Gestione classi ed ereditarietà
  ```
  class Fluit:
    def __init__(self,name,color):
      self.name=name
      self.color=color
    def detail(self):
      print ("my "+self.name +" is " + self.color) 
  my_apple = Fuit("apple","red")
  my_apple.detail()
  class Banana(Fuit):
    def __init__(self):
      super().__init__("banana","yellow")
      self.__cost=50 ##__cost is private
  my_b=Banana()
  # my_B.__cost #error !
  print ( my_B,_Banana__cost ) #works! private? no!
  ```
- Ordinare una lista di oggetti secondo un campo
  self.list = sorted( self.list , key=lambda tup: tup["campo"] , reverse=False )
- Funzioni lambda
  ```
	f = lambda a : a*a
  ```
- functioni con return multiplo
  ```
	def func():
		return 1,'alberto, True
	a,b,c=func()
	print( funct() )
  ```
- funzioni inline
  ```
	lista=[ e['Name'] for e in self.lista_bucket ]
	lista=[ e["Key"] if "Key" in e else e["Prefix"] for e in self.lista_files_bucket ]
  ```
- stringhe z=5
  ```
	s= f"Il quadrato di {z} è {z * z}"		len(s) 		s[3;6]  s[-2]
	s.startsWith("Il") s.endsWith("25"") s.isalnum() s.isdecimal() 
	da_fare=", ".join(lista ["pane","latte","melone" ] ) lista=da_fare.split(", ")
	print(f'{s:#<20})
  ```
- cicli
  ```
	for i in range(100)
		print("sorry")
  ```
- Dizionari https://www.youtube.com/watch?v=l0DDw4nzS_k
  ```
	ita_eng={"Ciao":"Hello","Uova":"Eggs"}		ita_eng.keys()  	.values()
	ita_eng.get("gatto","Chiave non trovata")
	ita_eng.setdefault("Birra","Beer") aggiunge valore se non presente
  ```  
- Gestione date
  ```
  from datetime import datetime, timedelta
  'createdAt': str (datetime.now() ) 
  yesterday = datetime.today() - timedelta(days = 1 )
  str_yesterday = yesterday.strftime("%Y%m%d")

  #convertire TS javascript a umano
  str_date=str(datetime.fromtimestamp( key['creationTime'] /1000 ) )

  #Recupero data in specifico formato
  from datetime import datetime 
  datetime.today().strftime('%Y%m%d %H%M%S')
  ```
- random
  ```
	import random
	import string
	base=["A","T","C","G"]
	s=rand.choises(baes, k=10) #k=numero di valori
	pwd="".join( random.choises(spring.printable,k=8) )
  ```
- json2csv # pip install pandas
  ```
	import pandas as pd
	pdObj = pd.read_json('20220824101456_SUPERB_ADV.json')
	print(type(pdObj))
	pdObj.to_csv('20220824101456_SUPERB_ADV.csv',sep=';',index=False)
  ```
- jwt
  ```
	import jwt
    key = "dancingPotatoes_!"
    auth = 'Deny'
    code = event['authorizationToken']
    # Decode JSON Web Token
    try:
        jwt.decode(code, key, algorithms="HS256")
        auth = 'Allow'
        logger.info('Valid key. Authorised User...')
    except:
        auth ='Deny'
        logger.info('Invalid key. Unauthorised User...')
  ```
- glob: libreria per file ma NON Usa reg-expression ma shell expression
  ```
	import glob
	print ( glob.glob ( '?pple.jpg' ))
	print ( glob.glob ( '*.jsp' ))
	print ( glob.glob ( '[ab]*.jpg' )) #a oppure b
	print ( glob.glob ( '[!z]*.jpg' )) #non inizia per z
	globs = glob.glob ( '**/*.jsp', root_dir='/.../' , recursive=True, include_hidden=True) #parametri vari
	print ( globs.__next__() )
	for i, file in enumerate (globs, 1):
		print (i, files, sep=": )
  ```
- py to exe https://www.youtube.com/watch?v=Y0HN9tdLuJo
  ```
    pip install auto-py-to-exe
  ```
- pandas to dictionary
  ```
	import pandas as pd 
	#df.to_dict: Turn a DataFrame into a Dictionary
	print ("---- DataFrame into Dictionary ---- ")
	df = pd.DataFrame({"fruits": ["apple", "orange", "grape"], "price": [1, 2, 3]})
	print ("---- DataFrame into Dictionary and records ---- ")
	d2=df.to_dict(orient="records")
	print (d2)
	[
		{'fruits': 'apple', 'price': 1}, 
		{'fruits': 'orange', 'price': 2}, 
		{'fruits': 'grape', 'price': 3}
	]
  ```
- visualizzare immagine	https://stackoverflow.com/questions/54103815/opencv-4-java-highgui-imshow
- boo https://stackoverflow.com/questions/54103815/opencv-4-java-highgui-imshow
- funzione per pulire il csv da caratteri lowvalue (caratteri di merda nei file fucos  https://stackoverflow.com/questions/7894856/line-contains-null-byte-in-csv-reader-python)
  ```
  def fix_nulls(s):
    for line in s:
        szRiga = line.replace('\0', ' ')
        szRiga = szRiga.replace('"', ' ')
        yield szRiga
  ```
- list  comprehension
  ```
  frutta=["mele","banana","peri"]
  for fuit in frutta:
    print(fuit)
    lista.append(fuit.upper() )
  [ print (fuit) for fruit in frutta ] #in una sola riga
  lista=[ fruit.upper() for fruit in frutta ]
  condition
  new_list=[ x for x in fruits if x!='apple']
  ---- dictionary comprehension
  lista=['Alberto','Andrea', 'Pietro']
  lista2=['Programamtore','Impiegato','Pensionato']
  d={}
  for (key,value) in zip(lista,lista2)
    m[key]=value
  d2={ key:value for (key,value) in zip(lista,lista2) }
  d3={ lista[i]:lista2[i] for i in range(len(lista)) }
  d4= { key+"man";val for (key,val) in d3.items() } #.items() è obbligatorio
  d5= { key+"man" if key != 'Pietro' else 'Paolo':val for (key,val) in d3.items() }
  d6= { key:[val, None] for (key,val) in enumerate["A","T","C","G"] }
    keys=["id","username","password"]
    users=["alnao","alberto.nao"]
  d7= [ {key:(i if key=="id" else users[i] if key=="useranme" else pwd for key in keys} for i in range(len(users))]
  ```
- json https://www.youtube.com/watch?v=7MKJEvTxL0c&list=PLMP9hIwoX2DtrBeIDXggVbo49Uxr6ymxT&index=5
  ```
  import requests
  import json
  url="https://xxxx"
  todos=requests.get(url).json()
  for todo in todos:
    val=todo["value"]
    print(val)
  ```
- wiki
  ```
  import wikipediaapi
  wiki = wikipediaapi.wikipedia('en')
  mon=['Jenuary']
  years=[x for x in range (1992,2022) ]
  pages=[]
  for year in years:	
    for month in months:
      pages.append("D..."+month
  existangce=[]
  for page in pages:
    page_py=wiki.page(page)
    existances.append(page_py.exists() )
    print(page_py.title)
  ```
- terminare script https://lorenzoneri.com/come-terminare-uno-script-python/?utm_source=dlvr.it&utm_medium=linkedin&utm_campaign=come-terminare-uno-script-python
  ```
  import sys
  sys.exit()
  ```

- esempio pandas legge un csv e fa 
  ```
	import pandas as pd
	pd.options.display.max_rows = 999999
	df = pd.read_csv('data.csv')
	di = dict(zip(list(df.Duration), list(df.Maxpulse)))
	#di è un dizionario
	d = (zip(list(df.Duration), list(df.Maxpulse)))
	#
	dii={}
	for k in d:
		dii[k[0]]=k[1]
	print(dii)
	print(dii['A61'])
  ```
- **f-string** da python3.12 
  ```
	stringhe speciali con f : interpolazione (string interpolation)
		variabile=42
		s=f"Numero = {variabile}"
		print(s) #Numero = 42
		s=f"Numero = {variabile + variable2}" #ok!
	con Py3.12 : eliminate le limitazioni
		libro={ "titolo":"Sig Anelli", "autore":"Tolkien"}
		s=f"Libro {libro["Titolo"] ora è possibile}
		s=f="Scrivo {"\n"} che non era possibile con 3.11 ora"
		s=f"""Questa string ha 3 doppi appici così è multilinea{
			libro['autore'].lower() # e ora possibile mettere i commenti
		} chiudo qua """
  ```
- enumerazioni e description (CLASSIFICATION SCHEME) con la classe Enum
  ```
	from enum import Enum
	class ColorePrimario(Enum):
		ROSSO=1
		VERDE=2
		BLU=3
	class PuntoCardinale(Enum):
		NORD='N'
		SUD='S'
		OVEST='O'
		EST='E'
	for direzione in PuntoCardinale:
		print(f"Nome: {direzione.name}, Valore: {direzione.value}")
	print(PuntoCardinale.SUD == PuntoCardinale.NORD) #FLASE
	print(PuntoCardinale.SUD == PuntoCardinale.SUD)
	print(PuntoCardinale.SUD == PuntoCardinale.SUD2) 
	print(PuntoCardinale.SUD is PuntoCardinale.NORD) #FALSE
	print(PuntoCardinale.SUD is PuntoCardinale.SUD2) #TRUE #DUE MEMBRI CON LO STESSO VALORE SONO VISTI COME LO STESSO
	print(PuntoCardinale.SUD == 'S' ) #FALSE
	print(PuntoCardinale.SUD.value == 'S' ) #TRUE
  ```
- Siti interessanti di riferimento:
  - Create a GUI app with Tkinter - Step by Step Tutorial https://www.youtube.com/watch?v=itRLRfuL_PQ
  - Machine Learning FOR BEGINNERS - Supervised, Unsupervised and Reinforcement Learning https://www.youtube.com/watch?v=mMc_PIemSnU
  - Guida Convert py to exe - from code to software https://www.youtube.com/watch?v=Y0HN9tdLuJo
  - Come eseguire gli script python all’avvio di Raspberry Pi https://www.moreware.org/wp/blog/2022/05/17/come-eseguire-gli-script-python-allavvio-di-raspberry-pi/
  - Pickle https://www.youtube.com/watch?v=6Q56r_fVqgw
  - Flask https://www.youtube.com/watch?v=pXMwAD9zMeg
  - Django https://www.youtube.com/watch?v=EEiqGjCNLRs



# &lt; AlNao /&gt;
Tutti i codici sorgente e le informazioni presenti in questo repository sono frutto di un attento e paziente lavoro di sviluppo da parte di AlNao, che si è impegnato a verificarne la correttezza nella massima misura possibile. Qualora parte del codice o dei contenuti sia stato tratto da fonti esterne, la relativa provenienza viene sempre citata, nel rispetto della trasparenza e della proprietà intellettuale. 


Alcuni contenuti e porzioni di codice presenti in questo repository sono stati realizzati anche grazie al supporto di strumenti di intelligenza artificiale, il cui contributo ha permesso di arricchire e velocizzare la produzione del materiale. Ogni informazione e frammento di codice è stato comunque attentamente verificato e validato, con l’obiettivo di garantire la massima qualità e affidabilità dei contenuti offerti. 


Per ulteriori dettagli, approfondimenti o richieste di chiarimento, si invita a consultare il sito [AlNao.it](https://www.alnao.it/).


## License
Made with ❤️ by <a href="https://www.alnao.it">AlNao</a>
&bull; 
Public projects 
<a href="https://www.gnu.org/licenses/gpl-3.0"  valign="middle"> <img src="https://img.shields.io/badge/License-GPL%20v3-blue?style=plastic" alt="GPL v3" valign="middle" /></a>
*Free Software!*


Il software è distribuito secondo i termini della GNU General Public License v3.0. L'uso, la modifica e la ridistribuzione sono consentiti, a condizione che ogni copia o lavoro derivato sia rilasciato con la stessa licenza. Il contenuto è fornito "così com'è", senza alcuna garanzia, esplicita o implicita.


The software is distributed under the terms of the GNU General Public License v3.0. Use, modification, and redistribution are permitted, provided that any copy or derivative work is released under the same license. The content is provided "as is", without any warranty, express or implied.

