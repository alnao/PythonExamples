# AwsLambdaExamples

## py-example3
Creazione con comando e template https://www.serverless.com/framework/docs/providers/aws/cli-reference/create
```
$ sls create --template aws-python3 --path py-example3-iam
```

Per la versione 2 di serverless usare la versione del pacchetto corrispondente
```
npm install -g serverless@2.72.3
```

Modifica del file `handler.py` con il codice della lambda
> Prestare attenzione che i tab non devono esserci ma devono essere 4 spazi.
```
import boto3

def hello(event, context):
    client = boto3.client('lambda')
    response = client.list_functions()
    return response

```

Modifica al file `serverless.yml`  per gestire diversi timout : crea due lambda con lo stesso codice ma con timeout diversi
```
provider:
  name: aws
  runtime: python3.8
  lambdaHashingVersion: 20201221 
  profile: serverless-admin
  region: us-east-1
  iam:
    role:
      statements:
        - Effect: "Allow"
          Action:
            - "lambda:*"
          Resource: 
            - "*"
functions:
  hello:
    handler: handler.hello

```
Eseguire il deploy la prima volta con 
```
$ cd py-example3-iam/
$ sls deploy -v
```
oppure deploy successivi della sola funzione specifica con
```
$ sls deploy function -f hello
```
il secondo è più veloce perchè deploya solo la funzione specifica.
Esito del deploy indica tutte le info

Dopo il deploy lanciare da console oppure lanciare da CLI la
```
$ sls invoke -f hello -l

```

## Per tutte le lambda create
Gestione dei log da AWS lambda dentro il Pannello di controllo nelle chiamate ed esecuzioni e su monitoraggio si vedono i log in CloudWatch Logs InsightsInfo
Oppure da riga di comando con
```
$ sls logs -f <nome> --startTime 5h
```
per vedere le ultime 5 ore oppure in tail con il comando
```
$ sls logs -f <nome> -t 
```
Per rimuovere tutto basta lanciare il comando da dentro la cartella della lambda
```
$ sls remove
```
questo comando rimuove la lambda, i bucket s3, i log e le dipendenze (non l'utenza IAM serverless-admin)

## License
**Free Software, Hell Yeah!**
Documento inizialmente creato con https://dillinger.io/ poi modificato a mano