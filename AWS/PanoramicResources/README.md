# AWS Resources Manager - Simple Dashboard

Dashboard semplice per visualizzare le risorse AWS del tuo account utilizzando Flask e Bootstrap.

## Funzionalità

- **Selezione dinamica di regione e profilo AWS**
- **Visualizzazione delle risorse AWS principali:**
  - VPC di default e componenti di rete (subnets, IGW, NAT Gateway)
  - Security Groups
  - Repository ECR
  - Cluster EKS e nodi
  - Istanze EC2
  - Database RDS
  - Bucket S3
  - Distribuzioni CloudFront
  - Stack CloudFormation
  - Allarmi CloudWatch
  - Funzioni Lambda
  - Tabelle DynamoDB
  - Code SQS
  - Topic SNS
  - API Gateway REST APIs

## Prerequisiti

- Python 3.7+
- Credenziali AWS configurate (file ~/.aws/credentials o variabili d'ambiente)
- Account AWS con i permessi appropriati per leggere le risorse

## Installazione

1. Clona o scarica il progetto
2. Installa le dipendenze:
   ```bash
   pip install -r requirements.txt
   ```

## Configurazione AWS

Assicurati di avere le credenziali AWS configurate. Puoi farlo in diversi modi:

### Metodo 1: AWS CLI
```bash
aws configure
```

### Metodo 2: File di credenziali
Crea il file `~/.aws/credentials`:
```ini
[default]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY

[profile-name]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
```

### Metodo 3: Variabili d'ambiente
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=eu-central-1
```

## Avvio dell'applicazione

```bash
python ManagerSimple.py
```

L'applicazione sarà disponibile all'indirizzo: http://localhost:5042

## Utilizzo

1. Apri il browser e vai a http://localhost:5042
2. Nella sezione "Configurazione AWS", seleziona:
   - La regione AWS desiderata
   - Il profilo AWS da utilizzare
3. Clicca su "Aggiorna" per ricaricare le risorse con la nuova configurazione
4. Esplora le diverse sezioni per visualizzare le tue risorse AWS

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

- **Non committare mai le tue credenziali AWS nel codice**
- Usa sempre profili AWS o variabili d'ambiente
- Assicurati che l'account AWS abbia solo i permessi minimi necessari
- Non esporre questa applicazione su reti pubbliche senza autenticazione

## Troubleshooting

### Errore "No credentials found"
- Verifica che le credenziali AWS siano configurate correttamente
- Controlla che il profilo selezionato esista

### Errore "Access Denied"
- Verifica che l'utente AWS abbia i permessi per accedere alle risorse
- Alcune operazioni richiedono permessi specifici (es. IAM, CloudFormation)

### Nessuna risorsa visualizzata
- Controlla che la regione selezionata sia corretta
- Verifica che ci siano effettivamente risorse nella regione selezionata

## Note

- Questo è uno strumento di visualizzazione in sola lettura
- Non vengono effettuate modifiche alle risorse AWS
- L'applicazione è ottimizzata per un uso locale/sviluppo
- Per l'uso in produzione, considera l'aggiunta di autenticazione e HTTPS

## License

MIT License - Vedi il file LICENSE per i dettagli
