# Aws Lambda example1
Questo esempio illustra come realizzare una funzione AWS Lambda in Python utilizzando il Serverless Framework versione 3. L’obiettivo è mostrare la configurazione essenziale del progetto, dalla definizione del provider fino alla gestione del deployment. Viene utilizzato un handler di base per rispondere agli eventi Lambda, con una struttura facilmente estendibile. La soluzione consente di automatizzare il ciclo di vita della funzione, semplificando la gestione delle risorse cloud e dei log.

- Creazione con comando e template https://www.serverless.com/framework/docs/providers/aws/cli-reference/create
  ```
  $ sls create --template aws-python3 --path py-example1
  ```
- Per la versione recente di serverless usare la versione del pacchetto corrispondente
  ```
  npm install -g serverless@latest
  ```
- Modifica del file `handler.py`
- Modifica al file `serverless.yml` (aggiunte le ultime 2 se non presenti, occhio alla regione che bisogna indicarla con precisione)
  ```
  provider:
    name: aws
    runtime: python3.9
    lambdaHashingVersion: 20201221
    profile: default
    region: eu-central-1
    stage: dev
  ```
  - verificare il profilo e la regione di destinazione!
- Eseguire il deploy la prima volta con 
  ```
  $ cd py-example1/
  $ sls deploy
  ```
- Le risorse create si vedono da *CloudFormation* e sono:
  | Risorsa                        | Nome                                                        | Tipo AWS                |
  |---------------------------------|-------------------------------------------------------------|-------------------------|
  | HelloLambdaFunction            | lambda-py-example1-dev-hello                                | AWS::Lambda::Function  |
  | HelloLogGroup                  | /aws/lambda/lambda-py-example1-dev-hello                    | AWS::Logs::LogGroup    |
  | IamRoleLambdaExecution         | lambda-py-example1-dev-eu-central-1-lambdaRole              | AWS::IAM::Role         |
  | ServerlessDeploymentBucket     | lambda-py-example1-dev-serverlessdeploymentbucket-u7hlsz6j0xd5 | AWS::S3::Bucket        |
  | ServerlessDeploymentBucketPolicy| lambda-py-example1-dev-serverlessdeploymentbucket-u7hlsz6j0xd5 | AWS::S3::BucketPolicy  |
- Per i deploy successivi del solito codice della funzione specifica con
  ```
  $ sls deploy function -f hello
  ```
  - il secondo è più veloce perchè deploya solo la funzione specifica.
  - Esito del deploy indica tutte le info
- Dopo il deploy lanciare da console oppure lanciare da CLI con
  ```
  $ sls invoke -f hello -l
  -----------------------------------------------------------
  {
      "statusCode": 200,
      "body": "{\"message\": \"Go Serverless v1.0! Your function executed successfully!\", \"input\": {}}"
  }
  --------------------------------------------------------------------
  START
  END Duration: 1.26 ms (init: 69.71 ms) Memory Used: 31 MB
  ```
- Gestione dei log da AWS lambda dentro il Pannello di controllo nelle chiamate ed esecuzioni e su monitoraggio si vedono i log in CloudWatch Logs InsightsInfo oppure da riga di comando con
  ```
  $ sls logs -f hello --startTime 5h
  ```
  - per vedere le ultime 5 ore oppure in tail con il comando
    ```
    $ sls logs -f hello -t 
    ```
- Per rimuovere tutto basta lanciare il comando da dentro la cartella della lambda
  ```
  $ sls remove
  ```
  - questo comando rimuove la lambda, i bucket s3, i log e le dipendenze (non l'utenza IAM serverless-admin)



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

