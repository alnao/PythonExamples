# CDK01 BucketS3
Esempio base per la creazione di un bucket

Per l'installazione e la configurazione della CLI e del tool CDK, vedere il file README esterno.

## Comandi
- Creazione del progetto
    ```
    mkdir Cdk01-bucketS3
    cd Cdk01-bucketS3
    cdk init app --language python
    python3 -m pip install -r requirements.txt
    python3 -m venv .venv
    ../bootstrap/bootstrap.sh create   # una volta per account: bootstrap con i nomi del repository (AWS/CDK/bootstrap)
    ```
- Deploy del progetto
    ```
    cdk ls
    cdk synth > BucketS3-template.yaml
    cdk deploy      
    ```
- Verifica del bucket 
    ```
    aws s3 ls
    aws s3 ls cdk-01-bucket-s3
    aws cloudformation list-stack-resources --stack-name Cdk01BucketS3Stack --output text
    aws cloudformation get-template --stack-name Cdk01BucketS3Stack
    ```
- Confronto tra sviluppo e ambiente target
    ```
    cdk diff 
    ```
- Distruzione dello stack con rimozione di tutte le risorse
    ```    
    cdk destroy
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


