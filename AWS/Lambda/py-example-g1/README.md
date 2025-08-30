# AwsLambdaExamples Google

## py-example-google1
Creazione con comando e template https://www.serverless.com/framework/docs/providers/aws/cli-reference/create
```
$ sls create --template google-python --path py-example-g1
$ cd py-example-g1/
$ sls plugin install -n serverless-google-cloudfunctions
```

Modifica al file `serverless.yml` (modificata versione )
```
frameworkVersion='3'
```

Eseguire il deploy la prima volta con 
```
$ sls deploy -v
```
oppure deploy successivi della sola funzione specifica con
```
$ sls deploy function -f py-example-g1
```
il secondo è più veloce perchè deploya solo la funzione specifica.
Esito del deploy indica tutte le info
Dopo il deploy lanciare da console oppure lanciare da CLI con
```
$ sls invoke -f py-example-g1 -l
```

## Per le credenziali di acesso seguire la guida ufficaile
https://serverless.com/framework/docs/providers/google/guide/credentials/

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