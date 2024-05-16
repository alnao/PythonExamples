# Esempio 05 applicazione flask con login SAML-SSO
Applicazione web flask con login Saml-SSO 

Riferimenti
- libreria [SAML-Toolkits](https://github.com/SAML-Toolkits/python-saml/tree/master)
    ```
    git clone https://github.com/SAML-Toolkits/python-saml/tree/master
    ```
    Nota: la libreria ha licenza **MIT License**
- ssl-https [SSL in Flask](https://stackoverflow.com/questions/29458548/can-you-add-https-functionality-to-a-python-flask-web-server)
    ``` 
    pip install pyopenssl
    cd localCert
    openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
    ``` 
    Esempio di codice Python 
    ``` 
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
``` 
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
```
docker build . -t flask-test-saml
docker run -d -p 8001:8001 flask-test-saml
docker ps
docker logs --follow xxx
docker stop xxx
```

### Docker files
```
FROM python:3.8
RUN  apt-get update
RUN  apt-get -y install libxml2-dev libxmlsec1-dev libxmlsec1-openssl
WORKDIR /project
ADD . /project
RUN pip install -r requirements.txt
CMD ["python","main.py"]
```


# AlNao.it
Nessun contenuto in questo repository è stato creato con IA o automaticamente, tutto il codice è stato scritto con molta pazienza da Alberto Nao. Se il codice è stato preso da altri siti/progetti è sempre indicata la fonte. Per maggior informazioni visitare il sito [AlNao.it](https://www.alnao.it/).

## License
Public projects 
<a href="https://it.wikipedia.org/wiki/GNU_General_Public_License"  valign="middle"><img src="https://img.shields.io/badge/License-GNU-blue" style="height:22px;"  valign="middle"></a> 
*Free Software!*