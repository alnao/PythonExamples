# Aws Lambda example5-sqs-get
Questo esempio illustra come realizzare una funzione AWS Lambda in Python utilizzando il Serverless Framework versione 3.


Note: in python code there are comments about Image library to create a thumbnail

To use serverless-python-requirement (like npm install)

```
$ serverless plugin install -n serverless-python-requirements
```

For vesion2 of serverless must use a version2 of pacakge
```
npm install -g serverless@2.72.3
```


To create 

```
$ sls create --template aws-python3 --path py-example6-sqs-get
```

Check `yml` file to bucket roles , destination is created inside yml, it doen't work if bucket is create manually!

To deploy

```
$ sls deploy -v
```


To invoke
```
$ sls invoke -f sqsget
```


To destroy ALL components (with entpy S3 bucket)

```
$ sls remove
```



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

