# Aws Lambda example3
Questo esempio illustra come realizzare una funzione AWS Lambda in Python utilizzando il Serverless Framework versione 3. 

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

