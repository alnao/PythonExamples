# AWS CDK 29 - API GraphQL con AppSync

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Una API **GraphQL** "listaNote" con **AWS AppSync**, che legge e scrive le note direttamente in **DynamoDB** con resolver VTL (nessuna Lambda), e una pagina web su **CloudFront** che si aggiorna da sola grazie alle **subscription**. Versione CDK in Python dell'esempio CloudFormation [Esempio29GraphQL](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio29GraphQL).

- **📐 Schema** in [graphql/schema.graphql](./graphql/schema.graphql): query `getNote`, mutation `addNota` e `deleteNota`, subscription `onAddNota` e `onDeleteNota`
- **⚙️ Resolver VTL su DynamoDB**: `Scan`, `PutItem` con id generato da `$util.autoId()` e data di creazione, `DeleteItem`; i valori passano da `$util.dynamodb.toDynamoDBJson`, quindi un testo con virgolette non rompe la richiesta, e un testo vuoto o oltre 500 caratteri riceve un errore di validazione
- **🔔 Tempo reale**: la pagina apre un WebSocket verso l'endpoint *realtime* di AppSync; una nota aggiunta o cancellata da un'altra finestra (o da curl) compare subito, senza ricaricare
- **🔑 API key** valida 365 giorni (CDK la ricalcola a ogni deploy; nel CloudFormation la scadenza era un numero fisso da aggiornare a mano)
- **📜 Log** degli errori dei resolver in CloudWatch, 7 giorni
- **🌐 Pagina web** su S3 privato dietro CloudFront, con URL e chiave della API in `config.json` (nel CloudFormation andavano scritti a mano nell'HTML)

Attenzione: con l'autenticazione a **API key** la chiave è leggibile da chiunque apra la pagina, quindi chiunque conosca il sito può leggere e scrivere le note. Va bene per un esempio; per dati veri servono Cognito o IAM (vedi gli sviluppi futuri).


## 🔧 Architettura

```
browser ── CloudFront ── bucket S3 privato (index.html, app.js, config.json con URL e chiave)
browser ── HTTPS POST https://xxx.appsync-api.<region>.amazonaws.com/graphql (x-api-key)
             ├── getNote    ── resolver Scan       ──┐
             ├── addNota    ── resolver PutItem    ──┼── data source ── DynamoDB <stack>-listaNote
             └── deleteNota ── resolver DeleteItem ──┘
browser ── WebSocket wss://xxx.appsync-realtime-api.<region>.amazonaws.com/graphql (graphql-ws)
             └── onAddNota, onDeleteNota: AppSync inoltra il risultato di ogni mutation ai client iscritti
```

```
├── app.py                     # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk29graph_ql/
│   ├── cdk29graph_ql_stack.py # 🏗️ API AppSync, API key, log, tabella, resolver, sito su CloudFront
│   └── tags.py                # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── graphql/schema.graphql     # 📐 schema GraphQL
├── web/                       # 🌐 index.html e app.js (fetch per query e mutation, WebSocket per le subscription)
├── tests/unit/                # 🧪 test dello stack (sintesi locale, senza AWS)
└── cdk.json, requirements*.txt
```


## 🛠️ Deploy

```bash
cd PythonExamples/AWS/CDK/cdk29GraphQL/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit

#../bootstrap/bootstrap.sh create eu-central-1
cdk deploy
```
Al termine `cdk deploy` stampa `SiteUrl` (la prima distribuzione CloudFront impiega qualche minuto), `GraphQLApiUrl`, `GraphQLApiKey`, `GraphQLApiId` e `DynamoTableName`.

Prova con curl (con la pagina aperta in un'altra finestra si vede la subscription in azione):
```bash
out() { aws cloudformation describe-stacks --stack-name Cdk29GraphQlStack --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
URL=$(out GraphQLApiUrl); KEY=$(out GraphQLApiKey)
gql() { curl -s $URL -H "Content-Type: application/json" -H "x-api-key: $KEY" -d "$1"; echo; }
gql '{"query": "mutation { addNota(testo: \"Comprare il latte\") { id testo createdAt } }"}'
gql '{"query": "query { getNote { id testo createdAt } }"}'
gql '{"query": "mutation Del($id: ID!) { deleteNota(id: $id) }", "variables": {"id": "<id>"}}'
gql '{"query": "mutation { addNota(testo: \"\") { id } }"}'      # errore di validazione
```
La console di AppSync ha anche un editor delle query (*Queries*) con lo schema e l'autocompletamento.

Comandi utili:
```bash
aws appsync list-graphql-apis --query "graphqlApis[].[name,apiId,uris.GRAPHQL]" --output table
aws appsync list-api-keys --api-id <GraphQLApiId> --query "apiKeys[].[id,expires]" --output table
aws appsync get-introspection-schema --api-id <GraphQLApiId> --format SDL schema.graphql
aws dynamodb scan --table-name Cdk29GraphQlStack-listaNote --query "Items[].testo.S"
aws logs tail /aws/appsync/apis/<GraphQLApiId> --since 1h
```

**Tag**: tutte le risorse hanno i tag standard del repository (`Project=Development.aws.py-CDK.cdk29GraphQL`, `ManagedBy=CDK`), comprese le Lambda di supporto di CDK (copia del sito, svuotamento del bucket). Non hanno tag solo i tipi che CloudFormation non permette di taggare: API key, schema, data source e resolver di AppSync, OAC, layer Lambda, policy IAM inline, policy del bucket.


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS e di [AWS AppSync](https://aws.amazon.com/appsync/pricing/). Lo stack non ha costi fissi.

Scenario: 10 persone che usano la pagina un'ora al giorno, 1.000 operazioni al giorno.
| Voce | Calcolo | Al mese (30 gg) |
|------|---------|-----------------|
| AppSync query e mutation | 30.000 × 4 $/milione | 0,12 $ |
| AppSync tempo reale | 18.000 minuti di connessione × 0,08 $/milione + ~100.000 messaggi × 2 $/milione | 0,20 $ |
| DynamoDB on-demand | 30.000 operazioni + pochi KB | 0,03 $ |
| CloudFront e S3 | dentro il free tier | 0 $ |
| CloudWatch Logs | solo errori, 7 giorni | ~0 $ |
| **Totale** | | **~0,35 $** |

Le subscription di AppSync costano molto meno delle connessioni WebSocket di API Gateway usate nel [cdk30WebSocket](../cdk30WebSocket/): sono una delle alternative economiche indicate nel README di quell'esempio.


## 🧹 Pulizia

```bash
cdk destroy
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk29GraphQL --query "ResourceTagMappingList[].ResourceARN" --output text
```
- API, chiave, tabella (con le note), log group, distribuzione CloudFront e bucket (svuotato da CDK) si cancellano con lo stack
- la Lambda di CDK che svuota il bucket scrive in un log group creato da Lambda, senza tag e non cancellato dallo stack: `aws logs describe-log-groups --log-group-name-prefix /aws/lambda/Cdk29GraphQlStack` e `aws logs delete-log-group --log-group-name <nome>`
- il bootstrap resta (condiviso con gli altri progetti CDK): `../bootstrap/bootstrap.sh destroy <region>` quando nella region non ci sono più stack CDK


## 🚀 Sviluppi Futuri
- 👤 **Autenticazione con Cognito** (note per utente, `@aws_cognito_user_pools`) e API key solo in lettura
- 🟨 **Resolver JavaScript** (runtime `APPSYNC_JS`) al posto di VTL e **pipeline resolver**
- 📄 **Paginazione** di `getNote` con `nextToken` invece di uno `Scan` completo
- ⚡ **Cache** di AppSync sulle query e un **dominio personalizzato**


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

