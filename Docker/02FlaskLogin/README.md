# Docker esempio 02 flask example
Sempice applicazione flask (web e API) che viene seguita dentro ad un docker 


Riferimenti di esempio:
- https://www.freecodecamp.org/news/how-to-dockerize-a-flask-app/
- https://www.digitalocean.com/community/tutorials/how-to-build-and-deploy-a-flask-application-using-docker-on-ubuntu-20-04
- https://medium.com/geekculture/how-to-dockerize-your-flask-application-2d0487ecefb8

Nota: è necessario il host nel comando  app.run(host="0.0.0.0", port=5000, debug=True)


# Comandi per la creazione l'esecuzione in sistema locale 
```bash
$ docker build . -t flask-login
$ docker run -it --rm -d -p 5001:5001 flask-login 
$ docker ps --latest

$ firefox http://localhost:5001

$ docker stop $(docker ps -q)
$ docker rm $(docker ps -a -q)
```


Per eseguire bash dentro alla immagine in esecuzione
```bash
$ docker exec -t -i $(docker ps -q) /bin/bash
```


Altri comandi specifici:
- https://www.docker.com/blog/how-to-use-the-official-nginx-docker-image/
    - docker run -it --rm -d -p 8087:80 --name web nginx
-  https://www.baeldung.com/ops/assign-port-docker-container
    - docker run -d -p 5001:80 --name httpd-container httpd


## Changelog
| Data | Modifica |
|------|----------|
| 2026-11-17 | Aggiunta la sezione Changelog |


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

