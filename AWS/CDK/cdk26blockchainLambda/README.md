# AWS CDK 26 - Blockchain con Lambda

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Una **blockchain didattica** serverless: le transazioni vanno in **DynamoDB**, una **Lambda** le raccoglie in un blocco con un algoritmo **proof of work** a bassa difficoltà (per spendere poco), le API sono su **API Gateway REST** e una pagina web su **CloudFront** permette di provare tutto dal browser. Versione CDK in Python dell'esempio CloudFormation [Esempio26blockchainLambda](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio26blockchainLambda), che aveva il codice Python dentro il template (`ZipFile`) e la pagina `index.html` da aprire in locale.

- **📝 Transazioni** `pending` finché un mining non le mette in un blocco, poi `mined` con l'indice del blocco (non vengono cancellate)
- **⛏️ Mining**: fino a 50 transazioni in attesa per blocco; l'hash SHA-256 di un'intestazione (`index|timestamp|tx_root|previous_hash|difficulty|nonce`) deve iniziare con 4 zeri esadecimali, in media 65.536 tentativi
- **🔗 Catena verificabile**: `GET /validate` ricalcola la radice delle transazioni e l'hash di ogni blocco e controlla il collegamento con il precedente; modificare una transazione già minata rende la catena non valida
- **💰 Saldi** di ogni indirizzo calcolati dalle sole transazioni minate
- **🔐 Una Lambda per operazione**, ognuna con i soli permessi DynamoDB che le servono (la Lambda delle transazioni può solo scrivere transazioni, quelle di lettura non scrivono)
- **🌐 Pagina web** su S3 privato dietro CloudFront, con l'URL delle API scritto da CDK in `config.json`

Differenze rispetto al template CloudFormation:
| | CloudFormation (Esempio26) | CDK (cdk26) |
|---|---|---|
| Codice Lambda | `ZipFile` dentro il template, ripetuto per ogni funzione | `lambda/api.py` e `lambda/chain.py`, testati in locale |
| Ultimo blocco | `scan(Limit=1)` (non garantisce l'ultimo) | tabella con chiave `chain` + `index`, `query` in ordine decrescente |
| Hash | JSON di tutto il blocco con importi float | intestazione con la radice delle transazioni, importi Decimal |
| Mining concorrente | due blocchi con lo stesso indice | scrittura condizionale: il secondo riceve `409` |
| Verifica | assente | `GET /blocks` e `GET /validate` |
| Pagina web | file locale con l'URL da modificare a mano | su CloudFront, URL delle API automatico |
| Limiti | nessuno | 10 richieste al secondo sullo stage `dev`, importi validati |


## 🔧 Architettura

```
browser ── CloudFront ── bucket S3 privato (index.html, app.js, config.json con l'URL delle API)
browser ── API Gateway REST, stage dev (CORS, 10 req/s) ──┬── POST /transaction  ── Lambda AddTransaction  ── Transactions (PutItem)
                                                          ├── POST /mine         ── Lambda MineBlock       ── Transactions + Blocks
                                                          ├── GET  /transactions ── Lambda GetTransactions ── Transactions
                                                          ├── GET  /balances     ── Lambda GetBalances     ── Transactions (StatusIndex = mined)
                                                          ├── GET  /blocks       ── Lambda GetBlocks       ── Blocks
                                                          └── GET  /validate     ── Lambda ValidateChain   ── Blocks
```

```
├── app.py                              # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk26blockchain_lambda/
│   ├── cdk26blockchain_lambda_stack.py # 🏗️ tabelle, Lambda, API Gateway, sito su CloudFront
│   └── tags.py                         # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── lambda/
│   ├── api.py                          # ⚡ una funzione per ogni operazione delle API
│   └── chain.py                        # ⛓️ hash, proof of work, verifica della catena, saldi (senza AWS)
├── web/                                # 🌐 index.html e app.js (Bootstrap da cdnjs)
├── tests/unit/                         # 🧪 test dello stack e delle Lambda (DynamoDB finto, senza AWS)
└── cdk.json, requirements*.txt
```

Tabelle (on-demand):
| Tabella | Chiave | Indice | Contenuto |
|---------|--------|--------|-----------|
| `<stack>-Blocks` | `chain` (sempre `main`) + `index` | - | blocco: transazioni, `tx_root`, `previous_hash`, `difficulty`, `nonce`, `hash` |
| `<stack>-Transactions` | `sender` + `timestamp` | `StatusIndex` (`status` + `timestamp`) | `id`, `recipient`, `amount`, `status`, `block_index` |


## 🛠️ Deploy

```bash
cd PythonExamples/AWS/CDK/cdk26blockchainLambda/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# test locali: sintesi dello stack e Lambda con DynamoDB finto
pytest tests/unit

#../bootstrap/bootstrap.sh create eu-central-1
cdk deploy
```
Al termine `cdk deploy` stampa `ApiUrl`, `SiteUrl` (la prima distribuzione CloudFront impiega qualche minuto), `BlocksTableName` e `TransactionsTableName`.

Prova con curl:
```bash
API_URL=$(aws cloudformation describe-stacks --stack-name Cdk26BlockchainLambdaStack --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text)
curl -X POST ${API_URL}transaction -H "Content-Type: application/json" -d '{"sender": "Root", "recipient": "Nao", "amount": 1984}'
curl -X POST ${API_URL}transaction -H "Content-Type: application/json" -d '{"sender": "Nao", "recipient": "Alice", "amount": 50}'
curl -X POST ${API_URL}transaction -H "Content-Type: application/json" -d '{"sender": "Nao", "recipient": "Vale", "amount": 42}'
curl -X POST ${API_URL}mine
curl ${API_URL}transactions
curl ${API_URL}balances
curl ${API_URL}blocks
curl ${API_URL}validate
```

Per vedere la verifica in azione si può "falsificare" un blocco già minato dalla console DynamoDB (cambiando l'importo di una transazione nella tabella `Blocks`): `GET /validate` risponde `"valid": false` con il motivo.

**Difficoltà**: la costante `DIFFICULTY` nello stack (default 4). Ogni zero in più moltiplica per 16 i tentativi: con 5 il mining richiede circa un milione di hash (qualche secondo), con 6 rischia di superare i 29 secondi di API Gateway. Il nonce trovato e la durata compaiono nella risposta di `POST /mine` e nel log della Lambda.

**Tag**: tutte le risorse hanno i tag standard del repository (`Project=Development.aws.py-CDK.cdk26blockchainLambda`, `ManagedBy=CDK`), comprese le Lambda di supporto di CDK (copia del sito, svuotamento del bucket). Non hanno tag solo i tipi che CloudFormation non permette di taggare: risorse, metodi e deployment di API Gateway, OAC, layer Lambda, permessi Lambda, policy IAM inline, policy del bucket.


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS. Lo stack non ha costi fissi: senza richieste costa praticamente zero.

Scenario: ogni giorno 200 transazioni, 20 mining e 500 letture dalla pagina.
| Voce | Calcolo | Al mese (30 gg) |
|------|---------|-----------------|
| API Gateway REST | ~22.000 richieste × 3,70 $/milione | 0,08 $ |
| Lambda | ~22.000 richieste; il mining ~1 s a 512 MB ARM (free tier: 1 milione di richieste e 400.000 GB-s) | 0 $ |
| DynamoDB on-demand | ~30.000 scritture × 1,525 $/milione + letture + pochi MB | 0,06 $ |
| CloudFront e S3 | dentro il free tier | 0 $ |
| CloudWatch Logs | pochi MB, 7 giorni | < 0,05 $ |
| **Totale** | | **~0,20 $** |

Le letture di `/transactions` e `/balances` leggono tutta la tabella: con molti dati il costo cresce con il numero di transazioni, non con le richieste (vedi gli sviluppi futuri).


## 🧹 Pulizia

```bash
cdk destroy
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk26blockchainLambda --query "ResourceTagMappingList[].ResourceARN" --output text
```
- tabelle, Lambda, log group, API, distribuzione CloudFront e bucket (svuotato da CDK) si cancellano con lo stack: la cancellazione della distribuzione CloudFront impiega qualche minuto
- la Lambda di CDK che svuota il bucket al destroy scrive in un log group creato da Lambda (`/aws/lambda/<stack>-CustomS3AutoDeleteObjects...`), senza tag e non cancellato dallo stack: si toglie con `aws logs delete-log-group --log-group-name <nome>`
- il bootstrap resta (condiviso con gli altri progetti CDK): `../bootstrap/bootstrap.sh destroy <region>` quando nella region non ci sono più stack CDK


## 🚀 Sviluppi Futuri
- 🎁 **Ricompensa del miner** e controllo del saldo prima di accettare una transazione (oggi qualsiasi indirizzo può andare in negativo, e negli esempi `Root` fa da emittente delle monete)
- ✍️ **Firme digitali**: transazioni firmate con una chiave privata e verificate dalla Lambda
- ⏱️ **Mining automatico** con EventBridge Scheduler e **difficoltà adattiva** sul tempo dei blocchi
- 📊 **Saldi incrementali** salvati a ogni blocco, invece di rileggere tutte le transazioni


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

