# Esempio 05 applicazione flask con login SAML-SSO
Applicazione web flask con login Saml-SSO 

Riferimenti
- libreria [SAML-Toolkits](https://github.com/SAML-Toolkits/python-saml/tree/master)
    ```bash
    git clone https://github.com/SAML-Toolkits/python-saml/tree/master
    ```
    Nota: la libreria ha licenza **MIT License**
- ssl-https [SSL in Flask](https://stackoverflow.com/questions/29458548/can-you-add-https-functionality-to-a-python-flask-web-server)
    ```bash
    pip install pyopenssl
    cd localCert
    openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
    ``` 
    Esempio di codice Python 
    ```bash
    if __name__ == "__main__":
        app.run(host='0.0.0.0', port=8001, debug=True , ssl_context=("./localCert/cert.pem", "./localCert/key.pem") )
    ``` 

## Struttura progetto
- cartella **onelogin**: con il pacakge scaricato dalla libreria [SAML-Toolkits](https://github.com/SAML-Toolkits/python-saml/tree/master), modificata e corretti errori di compilazione ed escluso il pezzo di verifica del certificato SAML perchè non funzionava
- cartella **localCert**: cartelle contentere i due certificati SSL creati con il comando ```openssl```
- cartella **saml**: file ```settings.json``` con configurati gli indirizzi dedicati
    - sp/entityId ```https://example.com:8001/```
    - sp/assertionConsumerService/url ```https://example.com:8001/servlet/saml/auth```
    - sp/singleLogoutService/url ```http://example.com:8001/?sls```
    - idp/entityId: ```https://login.microsoftonline.com/<id>/saml2```
    - idp/singleSignOnService/url: ```https://login.microsoftonline.com/<id>/saml2```
    - idp/singleLogoutService/url: ```https://login.microsoftonline.com/<id>/saml2```
- file **saml/certs/sp.crt**: file del certificato del server saml2, *verificare codice della libreria*
- cartella **templates**: 


## Comandi per l'installazione su Debian
Per la libreria ```dm.xmlsec.binding``` è necessario instlalare un libreria specifica:
```bash
sudo apt-get install libxmlsec1-dev
pip install -r requirements.txt
python3 main.py
```

### Comandi per i test
```
https://example.com:8001/withoutlogin
https://example.com:8001/withlogin
https://example.com:8001/
https://example.com:8001/withlogin
https://example.com:8001/attrs
https://example.com:8001/metadata
```

## Comandi per eseguire in docker
```bash
docker build . -t flask-test-saml
docker run -d -p 8001:8001 flask-test-saml
docker ps
docker logs --follow xxx
docker stop xxx
```

### Docker files
```dockerfile
FROM python:3.8
RUN  apt-get update
RUN  apt-get -y install libxml2-dev libxmlsec1-dev libxmlsec1-openssl
WORKDIR /project
ADD . /project
RUN pip install -r requirements.txt
CMD ["python","main.py"]
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

