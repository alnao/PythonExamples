# AWS CDK 30 - WebSocket: gioco "indovina il numero"

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Un piccolo gioco multigiocatore in tempo reale costruito con **API Gateway WebSocket**, **API Gateway HTTP API**, **Lambda** e **DynamoDB**, con le pagine web su **CloudFront**. Versione CDK in Python dell'esempio CloudFormation [Esempio30WebSocket](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio30WebSocket), riscritto con una sola logica di gioco testata in locale al posto di una Lambda per ogni funzione.

Le regole:
- ogni giocatore sceglie un **nickname** (5-30 lettere o cifre) e un **numero da 1 a 99** che nessun altro ha già scelto; il numero si può cambiare una volta ogni **24 ore**
- ogni giorno ha **5 tentativi** per indovinare il numero di un altro giocatore
- **numero indovinato**: +1 punto a chi attacca, -3 punti a chi lo aveva, che resta senza numero e può sceglierne subito un altro; la partita va nello storico e **tutti i giocatori collegati** ricevono la notizia via WebSocket
- **tentativo sbagliato**: -1 punto
- l'**amministratore** può mandare un messaggio a tutti, azzerare tutti i numeri, bannare (e riammettere) un giocatore; ogni giorno una Lambda toglie i giocatori fermi da più di 10 giorni

Componenti:
- **🔌 WebSocket API** (`$connect`, `$disconnect`, `$default`): la connessione si apre con `?nickname=` ed è accettata solo per un giocatore iscritto e non bannato; `{"action": "ping"}` tiene viva la connessione
- **🌐 HTTP API** con CORS e un limite di 20 richieste al secondo: gioco, classifica, storico, eventi e amministrazione
- **⚡ Lambda Python 3.13 ARM**: `api.py` (HTTP), `ws.py` (WebSocket e pulizia), regole in `game.py` (senza AWS, testate con tabelle finte)
- **🗄️ DynamoDB on-demand**: `Players`, `Matches`, `Logs` (partizione per giorno, scadenza automatica dopo 30 giorni) e `Bans`
- **🔑 Chiave di amministrazione** generata in Secrets Manager, nell'header `X-Admin-Key`
- **📄 Pagine** `index.html` (giocatore, classifica, partite) e `admin.html` su S3 privato dietro CloudFront, con gli indirizzi delle API in `config.json`

Differenze rispetto al template CloudFormation:
| | CloudFormation (Esempio30) | CDK (cdk30) |
|---|---|---|
| Lambda | 12 funzioni, una per operazione, più una per il CORS | 3 funzioni con la stessa logica (`game.py`) |
| API REST | API Gateway REST con risorsa `{proxy+}` e Lambda per OPTIONS | HTTP API con CORS gestito da API Gateway |
| Amministrazione | nessuna protezione | chiave in Secrets Manager (`X-Admin-Key`) |
| Associazione WebSocket | nickname mandato dopo la connessione | nickname nella richiesta di connessione, rifiutata se non iscritto o bannato |
| Log del gioco | tabella con chiave `timestamp`, letta con `scan` | partizione per giorno, `query`, TTL di 30 giorni |
| Numeri dei giocatori | visibili nei log degli eventi | mai esposti dalle API |
| Ban | il giocatore veniva cercato dopo averlo cancellato (nessun avviso) | avviso via WebSocket, poi cancellazione |
| Sito | bucket pubblico, indirizzi delle API da scrivere a mano nei file | bucket privato e CloudFront, `config.json` scritto da CDK |

Attenzione: il gioco non ha un'autenticazione dei giocatori, chiunque può usare un nickname (come nell'esempio CloudFormation).


## 🔧 Architettura

```
browser ── CloudFront ── bucket S3 privato (index.html, admin.html, *.js, config.json)
browser ── HTTPS ── HTTP API ($default, CORS, 20 req/s) ── Lambda Api ──┬── DynamoDB Players, Matches, Logs, Bans
                                                                        ├── Secrets Manager (chiave admin)
                                                                        └── @connections (notifiche ai giocatori)
browser ── wss ── WebSocket API (stage prod) ──┬── $connect ?nickname= ──┐
                                               ├── $disconnect ──────────┼── Lambda WebSocket ── Players, Logs
                                               └── $default (ping) ──────┘
EventBridge rate(1 day) ── Lambda Cleanup ── toglie i giocatori inattivi da 10 giorni
```

```
├── app.py                          # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk30web_socket/
│   ├── cdk30web_socket_stack.py    # 🏗️ tabelle, segreto, Lambda, WebSocket API, HTTP API, regola, sito
│   └── tags.py                     # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── lambda/
│   ├── game.py                     # 🎲 regole del gioco (tabelle e invio dei messaggi passati dall'esterno)
│   ├── aws.py                      # 🔗 tabelle boto3, post_to_connection, chiave admin
│   ├── api.py                      # ⚡ route della HTTP API
│   └── ws.py                       # 🔌 route WebSocket e pulizia giornaliera
├── web/                            # 🌐 index.html + game.js, admin.html + admin.js, common.js
├── tests/unit/                     # 🧪 test dello stack e del gioco (DynamoDB e WebSocket finti)
└── cdk.json, requirements*.txt
```

| Metodo | Percorso | Descrizione |
|--------|----------|-------------|
| POST | `/set-number` | `{"nickname": "...", "number": 42}` iscrizione o cambio del numero |
| POST | `/guess-number` | `{"attacker": "...", "guess": 13}` tentativo, risponde `hit`, `message`, `left` |
| GET | `/scores` | classifica (senza i numeri), con lo stato di gioco e di connessione |
| GET | `/matches` | storico delle partite |
| GET | `/logs` | eventi di oggi e di ieri (al massimo 100) |
| POST | `/admin/broadcast` | `{"text": "..."}` messaggio a tutti i giocatori collegati |
| POST | `/admin/reset` | azzera i numeri di tutti |
| POST | `/admin/ban`, `/admin/unban` | `{"nickname": "...", "reason": "..."}` |
| GET | `/admin/bans` | giocatori bannati |


## 🛠️ Deploy

```bash
cd PythonExamples/AWS/CDK/cdk30WebSocket/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# test locali: sintesi dello stack e gioco con DynamoDB e WebSocket finti
pytest tests/unit

#../bootstrap/bootstrap.sh create eu-central-1
cdk deploy
```
Al termine `cdk deploy` stampa `SiteUrl` (la prima distribuzione CloudFront impiega qualche minuto), `HttpApiUrl`, `WebSocketUrl` e `AdminKeyCommand`, il comando che legge la chiave da inserire nella pagina di amministrazione.

Prova da riga di comando (`wscat` si installa con `npm install -g wscat`):
```bash
out() { aws cloudformation describe-stacks --stack-name Cdk30WebSocketStack --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
API=$(out HttpApiUrl); WS=$(out WebSocketUrl)
curl -s -X POST $API/set-number -H "Content-Type: application/json" -d '{"nickname": "Alberto", "number": 42}'
curl -s -X POST $API/set-number -H "Content-Type: application/json" -d '{"nickname": "Andrea1", "number": 13}'
wscat -c "$WS?nickname=Andrea1"          # in un altro terminale: resta in ascolto delle notizie
curl -s -X POST $API/guess-number -H "Content-Type: application/json" -d '{"attacker": "Alberto", "guess": 13}'
curl -s $API/scores
curl -s $API/matches

KEY=$(aws secretsmanager get-secret-value --secret-id Cdk30WebSocketStack-AdminKey --query SecretString --output text)
curl -s -X POST $API/admin/broadcast -H "X-Admin-Key: $KEY" -H "Content-Type: application/json" -d '{"text": "Benvenuti!"}'
```

Comandi utili:
```bash
aws dynamodb scan --table-name Cdk30WebSocketStack-Players --query "Items[].[nickname.S,score.N,connectionId.S]" --output table
aws logs tail /aws/lambda/Cdk30WebSocketStack-Api --follow
aws logs tail /aws/lambda/Cdk30WebSocketStack-WebSocket --follow
aws lambda invoke --function-name Cdk30WebSocketStack-Cleanup /dev/stdout   # pulizia manuale
```

Cosa succede se un giocatore chiude il browser senza scollegarsi: API Gateway chiude la connessione e chiama `$disconnect`, che toglie il `connectionId`; il giocatore resta nel gioco con numero e punti, ma non riceve più notizie finché non rientra. Se una notifica trova una connessione già chiusa (`GoneException`), la Lambda toglie il `connectionId` da sola. API Gateway chiude comunque le connessioni inattive dopo 10 minuti e tutte dopo 2 ore: la pagina manda un ping ogni 5 minuti.

**Tag**: tutte le risorse hanno i tag standard del repository (`Project=Development.aws.py-CDK.cdk30WebSocket`, `ManagedBy=CDK`), comprese le Lambda di supporto di CDK (copia del sito, svuotamento del bucket). Non hanno tag solo i tipi che CloudFormation non permette di taggare: route e integrazioni di API Gateway, OAC, layer Lambda, permessi Lambda, policy IAM inline, policy del bucket.


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS e di [API Gateway](https://aws.amazon.com/api-gateway/pricing/). Lo stack ha come unico costo fisso il segreto (0,40 $ al mese).

| Voce | 10 giocatori | 10.000 giocatori |
|------|--------------|------------------|
| WebSocket, minuti di connessione (~0,29 $/milione) | 10 × 2 ore al giorno: 36.000 minuti → 0,01 $ | sempre collegati: 432 milioni di minuti → ~125 $ |
| WebSocket, messaggi (~1,14 $/milione, a blocchi di 32 KB) | qualche migliaio → 0 $ | 100 al giorno a testa: 30 milioni → ~34 $ |
| HTTP API (1,20 $/milione) | qualche migliaio → 0 $ | 30 milioni → ~36 $ |
| Lambda (ARM, 256 MB) | dentro il free tier | ~60 milioni di richieste brevi → ~15 $ |
| DynamoDB on-demand | pochi centesimi | ~60 milioni di operazioni + `scan` dei giocatori → 80-150 $ |
| Secrets Manager, CloudFront, S3, Logs | ~0,50 $ | ~10 $ |
| **Totale al mese** | **~0,50 $** | **~300-370 $** |

Note:
- il README dell'esempio CloudFormation stimava circa 1.800 € al mese per 10.000 giocatori contando 0,25 per connessione **all'ora**: il prezzo delle WebSocket API è invece per **milione di minuti** di connessione, quindi la stessa ipotesi costa circa 125 $
- con molti giocatori la voce più grande diventa DynamoDB, perché ogni tentativo e ogni notifica a tutti leggono l'intera tabella `Players` (`scan`): per crescere servirebbe un indice sui numeri e una tabella delle connessioni
- alternative più economiche per le notifiche, già indicate nell'esempio CloudFormation: polling su HTTP API, oppure le subscription di AppSync (vedi il [cdk29GraphQL](../cdk29GraphQL/))


## 🧹 Pulizia

```bash
cdk destroy
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk30WebSocket --query "ResourceTagMappingList[].ResourceARN" --output text
```
- tabelle (con giocatori e partite), segreto, Lambda, log group, API, regola, distribuzione CloudFront e bucket (svuotato da CDK) si cancellano con lo stack
- la Lambda di CDK che svuota il bucket scrive in un log group creato da Lambda, senza tag e non cancellato dallo stack: `aws logs describe-log-groups --log-group-name-prefix /aws/lambda/Cdk30WebSocketStack` e `aws logs delete-log-group --log-group-name <nome>`
- il bootstrap resta (condiviso con gli altri progetti CDK): `../bootstrap/bootstrap.sh destroy <region>` quando nella region non ci sono più stack CDK


## 🚀 Sviluppi Futuri
- 👤 **Autenticazione dei giocatori** con Cognito (token nella connessione WebSocket con un *authorizer* Lambda)
- 📇 **Indice sui numeri** e **tabella delle connessioni** per evitare gli `scan` con molti giocatori
- ⏰ **Regole a tempo** dell'idea originale: giocatore eliminato se non sceglie un numero entro un minuto, o se non lo cambia ogni 3 ore (EventBridge Scheduler)
- 🔁 Versione con le **subscription di AppSync** al posto di API Gateway WebSocket, per confrontare costi e complessità


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

