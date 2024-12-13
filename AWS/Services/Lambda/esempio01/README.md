# Aws Lambda Examples - Esempio 01

## Creazione del progetto
Creazione con comando e template, vedi [documentazione ufficiale](https://www.serverless.com/framework/docs/providers/aws/cli-reference/create)
Comando base per la creazione
```
$ serverless

>  AWS / Python / Simple Function
```
Esempio 
```
$ sls create --template aws-python3 --path esempio01
```

## Sviluppo base
Modificati i file 
- `serverless.yaml`
  ```
  org: alnao
  service: esempio01

  provider:
    name: aws
    runtime: python3.12
    region: eu-west-1

  functions:
    esempio01:
      handler: handler.hello
  ```
- `handler.py`
  ```
  import json
  def hello(event, context):
      print("esempio01", event)
      body = {
          "message": "Go Serverless v4.0! Your function executed successfully!"
      }
      return {"statusCode": 200, "body": json.dumps(body)}
  ```

## Rilascio
- Per rilasciare la lambda in un ambiente AWS
  ```
  serverless deploy   
  ```
- Per rimuovere la lambda 
  ```
  serverless remove   
  ```

## Invocazioni e logs
- Per invocare
    ```
    sls invoke -f esempio01
    sls invoke -f esempio01withParam
    ```
- Per vedere tutti i log delle ultime 5 ore
    ```
    $ sls logs -f esempio01 --startTime 5h
    ```
- Ultime esecuzioni 
    ```
    $ sls logs -f esempio01 -t 
    ```


# AlNao.it
Nessun contenuto in questo repository è stato creato con IA o automaticamente, tutto il codice è stato scritto con molta pazienza da Alberto Nao. Se il codice è stato preso da altri siti/progetti è sempre indicata la fonte. Per maggior informazioni visitare il sito [AlNao.it](https://www.alnao.it/).

## License
Public projects 
<a href="https://it.wikipedia.org/wiki/GNU_General_Public_License"  valign="middle"><img src="https://img.shields.io/badge/License-GNU-blue" style="height:22px;"  valign="middle"></a> 
*Free Software!*