
<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.8+" height=60/>
  <img src="https://img.shields.io/badge/AWS-Cloud-orange?style=for-the-badge&logo=amazon-aws&logoColor=white" alt="AWS" height=60/>
  <img src="https://img.shields.io/badge/AWS-Lambda-%23FF9900?style=for-the-badge&logo=AWSlambda&logoColor=black" height=60/>
</p>

# Aws Lambda Examples
AWS Lambda Examples by [AlNao](https://www.alnao.it).


Raccolta completa di esempi pratici per sviluppare e deployare AWS Lambda Functions in Python utilizzando la libreria boto, AWS SAM e diverse modalità di rilascio. Questi esempi non usano il servizio di CloudFormation per gestire le risorse AWS.


## Prerequisiti
Riferimento: [documentazione ufficiale AWS Lambda Java](https://docs.aws.amazon.com/lambda/latest/dg/java-package.html)
- Un account AWS attivo
- La AWS-CLI installata, [documentazione ufficiale](https://docs.aws.amazon.com/it_it/cli/v1/userguide/cli-chap-install.html)
- Utenza tecnica di tipo programmatico configurata su IAM con permessi di esecuzione di CloudFormation e configurazione della AWS-CLI con il comando
    - ```aws configuration```
- La AWS-CLI-SAM installata correttamente, [documentazione ufficiale](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
- Npm installato nel sistema per l'uso del comando ```serverless``` (abbreviato anche con ```sls```)
- Maven installato nel sistema per l'uso del linguaggio Java
- Pip installato nel sistema per l'uso del linguaggio Python


## Comandi per la creazione con SLS
Comandi per la configurazione di SLS
```
$ npm install -g serverless
$ serverless config credentials --provider aws --key <key> --secret <secret> --profile serverless-admin
$ servless
$ sls
```

## Esempi Python per AWS Lambda

- **py-example1**: Esempio base di Lambda in Python con Serverless Framework. Mostra la struttura minima di una funzione Lambda.
- **py-example2-timeout**: Gestione dei timeout nelle funzioni Lambda. Crea due funzioni con lo stesso codice ma timeout diversi per dimostrare il comportamento in caso di timeout.
- **py-example3-iam**: Configurazione dei permessi IAM per accedere ad altri servizi AWS. Usa boto3 per elencare le funzioni Lambda esistenti.
- **py-example4-enviroments-variables**: Utilizzo delle variabili d'ambiente nelle funzioni Lambda. Mostra come configurare variabili globali e specifiche per funzione.
- **py-example5-file-manager**: Gestione di file S3 con trigger automatico. Lambda che si attiva quando viene caricato un file in un bucket S3 e lo elabora.
- **py-example6-sqs-get**: Lettura di messaggi da una coda SQS. Mostra come configurare una Lambda per processare messaggi da Amazon SQS.
- **py-example6-sqs-post**: Invio di messaggi ad una coda SQS. Esempio di come una Lambda può pubblicare messaggi in una coda SQS.
- **py-example7-g1**: Esempio di funzione serverless per Google Cloud Functions usando il Serverless Framework.


## Comandi Comuni per Tutti gli Esempi

- Deploy completo (prima volta)
  ```bash
  cd [nome-esempio]/
  sls deploy -v
  ```
- Deploy di una singola funzione (più veloce)
  ```bash
  sls deploy function -f [nome-funzione]
  ```
- Invocazione della funzione
  ```bash
  sls invoke -f [nome-funzione] -l
  ```
- Visualizzazione dei log
  ```bash
  # Ultimi log (5 ore)
  sls logs -f [nome-funzione] --startTime 5h
  # Log in tempo reale
  sls logs -f [nome-funzione] -t
  ```
- Rimozione completa dello stack
  ```bash
  sls remove
  ```
- Note Importanti
  - Prestare attenzione all'indentazione in Python: usare 4 spazi invece dei tab
  - Configurare il profilo AWS con `aws configure` prima del primo deploy
  - La regione AWS deve essere specificata correttamente nel file `serverless.yml`
  - Per esempi che usano dipendenze Python, installare il plugin: `serverless plugin install -n serverless-python-requirements`



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

