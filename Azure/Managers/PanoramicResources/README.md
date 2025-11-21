# Azure Resources Manager - Simple Dashboard

Dashboard semplice per visualizzare le risorse Azure del tuo account utilizzando Flask e Bootstrap.

## Funzionalità

- **Selezione dinamica della subscription Azure**
- **Visualizzazione delle risorse Azure principali:**
  - Resource Groups
  - Virtual Machines
  - Virtual Networks
  - Storage Accounts
  - SQL Servers e Databases
  - App Services
  - Container Instances
  - Container Registries
  - Key Vaults
  - Cosmos DB Accounts
  - Network Security Groups
  - Public IP Addresses

## Prerequisiti

- Python 3.7+
- Azure CLI installato e configurato
- Account Azure con i permessi appropriati per leggere le risorse

## Installazione

1. Clona o scarica il progetto
2. Installa le dipendenze:
   ```bash
   pip install -r requirements.txt
   ```

## Configurazione Azure

Assicurati di avere le credenziali Azure configurate. Puoi farlo in diversi modi:

### Metodo 1: Azure CLI (Raccomandato)
```bash
az login
```

### Metodo 2: Service Principal
Crea le variabili d'ambiente:
```bash
export AZURE_CLIENT_ID=your_client_id
export AZURE_CLIENT_SECRET=your_client_secret
export AZURE_TENANT_ID=your_tenant_id
export AZURE_SUBSCRIPTION_ID=your_subscription_id
```

### Metodo 3: Managed Identity
Se esegui l'applicazione su una VM Azure o App Service, puoi usare Managed Identity.

## Avvio dell'applicazione

```bash
python3 ManagerSimple.py
```

L'applicazione sarà disponibile all'indirizzo: http://localhost:5043

## Utilizzo

1. Apri il browser e vai a http://localhost:5043
2. Nella sezione "Configurazione Azure", seleziona:
   - La subscription Azure da utilizzare
3. Clicca su "Aggiorna" per ricaricare le risorse con la nuova configurazione
4. Esplora le diverse sezioni per visualizzare le tue risorse Azure

## Struttura del progetto

```
PanoramicResources/
├── ManagerSimple.py          # Applicazione Flask principale
├── requirements.txt          # Dipendenze Python
├── README.md                # Questo file
└── templates/
    └── index.html           # Template HTML con Bootstrap
```

## Sicurezza

- **Non committare mai le tue credenziali Azure nel codice**
- Usa sempre Azure CLI authentication o variabili d'ambiente
- Assicurati che l'account Azure abbia solo i permessi minimi necessari (Reader role)
- Non esporre questa applicazione su reti pubbliche senza autenticazione

## Troubleshooting

### Errore "No credentials found"
- Verifica di aver eseguito `az login`
- Controlla che le credenziali Azure siano configurate correttamente

### Errore "Access Denied"
- Verifica che l'utente/service principal abbia i permessi per accedere alle risorse
- Assicurati di avere almeno il ruolo "Reader" sulla subscription

### Nessuna risorsa visualizzata
- Controlla che la subscription selezionata sia corretta
- Verifica che ci siano effettivamente risorse nella subscription
- Controlla i log dell'applicazione per eventuali errori

### Errore nell'importazione dei moduli
- Assicurati di aver installato tutte le dipendenze:
  ```bash
  pip install -r requirements.txt
  ```

## Permessi necessari

Per visualizzare tutte le risorse, l'account deve avere almeno il ruolo **Reader** a livello di subscription oppure sui singoli resource groups.

## Note

- Questo è uno strumento di visualizzazione in sola lettura
- Non vengono effettuate modifiche alle risorse Azure
- L'applicazione è ottimizzata per un uso locale/sviluppo
- Per l'uso in produzione, considera l'aggiunta di:
  - Autenticazione (Azure AD)
  - HTTPS
  - Rate limiting
  - Caching delle risorse

## Differenze rispetto alla versione AWS

- Usa Azure SDK invece di Boto3
- Autenticazione tramite Azure CLI o Service Principal
- Organizzazione basata su Subscriptions e Resource Groups
- Servizi Azure equivalenti (VM invece di EC2, Storage Accounts invece di S3, ecc.)



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

