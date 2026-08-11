# AWS Tag Manager

Applicazione Flask per **visualizzare e gestire i tag** di tutte le risorse AWS di una region,
versione web del comando:

```bash
aws resourcegroupstaggingapi get-resources --region "$R"
```

## Le due sorgenti dati (importante)

`get-resources` **non restituisce tutte le risorse**: per documentazione AWS torna
*"all the tagged or previously tagged resources"*, quindi le risorse **mai taggate**
non compaiono. Misurato su un account reale in `us-east-2`:

| sorgente | risorse trovate |
|---|---|
| `resourcegroupstaggingapi get-resources` | 37 |
| `resource-explorer-2 search` | 128 |
| unione (quella usata di default dall'app) | **129** |

Le 92 risorse esclusive di Resource Explorer erano tutte mai taggate: parameter group
MemoryDB, route e integration di API Gateway, versioni di Lambda, chiavi KMS, data catalog
Athena, event bus di default, security group rule. Sono le stesse che mostra il **Tag Editor
della console**, che infatti usa Resource Explorer e non la Tagging API.

L'app quindi legge da entrambe e unisce per ARN, con la tendina **Sorgente**:

- `Entrambe (completo)` — default, unione delle due
- `Solo Tagging API` — comportamento "classico", solo risorse già taggate
- `Solo Resource Explorer` — tutto ciò che è indicizzato

La colonna **Origine** dice da dove arriva ogni riga (`API tag`, `Explorer`, `Entrambe`).
Se una region non ha l'indice di Resource Explorer attivo, l'app continua a funzionare
con la sola Tagging API e lo segnala con un avviso giallo.

## Funzionalità

- **Selezione della region da una lista parametrica** (configurabile in `config.json`,
  sovrascrivibile con la variabile d'ambiente `AWS_REGIONS`) e del profilo AWS
- **Tabella di tutte le risorse** della region, con servizio, tipo, nome, ARN, tag e origine
- **Dettaglio completo** di ogni risorsa (dati estratti dall'ARN, elenco tag e JSON grezzo)
- **Filtri sui tag**, calcolati sull'elenco completo:
  - tutte le risorse
  - solo risorse **senza alcun tag**
  - solo risorse con almeno un tag
  - risorse **con una chiave specifica** (es. tutte quelle con `Environment`)
  - risorse **senza una chiave specifica** (utile per il governo dei costi)
  - risorse con **chiave = valore** (es. `Environment = prod`)
- **Ricerca testuale** su nome, ARN e tag, e filtro per servizio (lato browser, immediati)
- **Aggiunta e rimozione dei tag**, sulla singola risorsa o **in massa** sulle risorse selezionate
- **Tag rapido**: si scrivono chiave e valore sopra la tabella e si applicano con un solo clic
  riga per riga (o a tutte le selezionate). Il pulsante dice in anticipo cosa farà:
  verde ⚡ se **aggiunge** la chiave, arancione ✎ se **aggiorna** un valore diverso
  (col tooltip che mostra vecchio → nuovo), spento ✓ se il tag è già a posto
- **Card di riepilogo**: totale risorse, quante senza tag, quante con tag, servizi e chiavi distinte

## Prerequisiti

- Python 3.8+
- Credenziali AWS configurate (`~/.aws/credentials` o variabili d'ambiente)
- Permessi IAM:
  `tag:GetResources`, `tag:GetTagKeys`, `tag:GetTagValues`,
  `tag:TagResources`, `tag:UntagResources`, `ec2:DescribeRegions`,
  `resource-explorer-2:GetDefaultView`, `resource-explorer-2:Search`

La policy gestita `ResourceGroupsandTagEditorFullAccess` copre le prime, per Resource Explorer
serve in più `AWSResourceExplorerReadOnlyAccess`. Resource Explorer va **abilitato** nella
region (indice + vista di default): senza indice l'app funziona lo stesso, ma vede solo le
risorse già taggate.

## Installazione ed esecuzione

```bash
cd AWS/Managers/TagManager
pip3 install -r requirements.txt
python3 app.py
```

Poi aprire il browser su [http://localhost:5002](http://localhost:5002).

## Configurazione

La lista delle region mostrate nella tendina si trova in `config.json`:

```json
{
  "default_region": "eu-central-1",
  "default_profile": "default",
  "regions": ["eu-central-1", "eu-west-1", "us-east-1"],
  "suggested_tag_keys": ["Name", "Environment", "Project", "Owner"]
}
```

Il pulsante <kbd>🌍</kbd> nella barra in alto rilegge da AWS le region abilitate
sull'account (`ec2 describe-regions`) e riscrive la sezione `regions` del file.

Variabili d'ambiente che hanno la precedenza sul file:

| Variabile     | Descrizione                                   | Default        |
|---------------|-----------------------------------------------|----------------|
| `AWS_REGIONS` | lista region separate da virgola              | da config.json |
| `AWS_REGION`  | region preselezionata                         | da config.json |
| `AWS_PROFILE` | profilo preselezionato                        | da config.json |
| `PORT`        | porta di ascolto di Flask                     | `5002`         |

## Struttura del progetto

```
TagManager/
├── app.py              # applicazione Flask e API REST
├── tag_manager.py      # classe TagManager: resourcegroupstaggingapi + resource-explorer-2
├── config.json         # lista parametrica delle region e valori di default
├── requirements.txt
├── static/
│   ├── app.js          # logica della pagina (filtri, tabella, modali)
│   └── style.css
└── templates/
    └── index.html      # pagina Bootstrap 5
```

## API REST esposte

| Metodo | Endpoint               | Descrizione                                              |
|--------|------------------------|----------------------------------------------------------|
| GET    | `/api/resources`       | risorse della region filtrate (`source`, `filter_mode`, `tag_key`, `tag_value`, `refresh`) |
| GET    | `/api/tag-keys`        | chiavi tag presenti nella region                          |
| GET    | `/api/tag-values`      | valori di una chiave (`key`)                              |
| POST   | `/api/tags/add`        | aggiunge/aggiorna tag (`arns`, `tags`)                    |
| POST   | `/api/tags/remove`     | rimuove chiavi tag (`arns`, `tag_keys`)                   |
| POST   | `/api/regions/refresh` | rilegge le region da AWS e le salva in `config.json`      |

Esempio da riga di comando:

```bash
curl "http://localhost:5002/api/resources?region=us-east-2&source=both&filter_mode=untagged"

curl -X POST http://localhost:5002/api/tags/add \
  -H "Content-Type: application/json" \
  -d '{"region":"eu-west-1","arns":["arn:aws:s3:::mio-bucket"],"tags":{"Owner":"alnao"}}'
```

## Note tecniche

- L'applicazione legge sempre l'elenco completo e applica i filtri dopo: con i `TagFilters`
  lato AWS il filtro "senza tag" non sarebbe realizzabile.
- I tag mostrati per le risorse trovate solo da Resource Explorer vengono da un indice
  aggiornato in modo **asincrono**, quindi possono essere leggermente arretrati; per le
  risorse presenti in entrambe le sorgenti vincono sempre i tag della Tagging API.
- Non tutte le risorse elencate sono **taggabili**. I casi noti sono controllati prima di
  chiamare AWS (`check_taggable`), con regole verificate interrogando le API:

  | ARN | esito |
  |---|---|
  | `lambda:...:function:NOME` | taggabile |
  | `lambda:...:function:NOME:$LATEST` o `:1` | no — *"Tags on function aliases and versions are not supported"*, il tag va sulla funzione (l'app propone l'ARN giusto) |
  | `lambda:...:layer:NOME` e `layer:NOME:2` | no — *"Unsupported resource type for tagging"*: i layer non sono taggabili in nessuna forma |

  Per queste risorse il pulsante del tag rapido è spento con l'icona 🚫 e il motivo nel
  tooltip, e nelle operazioni multiple vengono scartate invece di far fallire il blocco.
  Tutto il resto viene tentato: se AWS rifiuta, l'errore arriva comunque all'utente.
- Le `ValidationException` di AWS contengono l'intera espressione regolare accettata dal
  servizio: in pagina viene mostrata una versione leggibile, mentre il testo integrale resta
  nel campo `failed_details` della risposta e nei log.
- La ricerca di Resource Explorer restituisce al massimo 1000 risorse per query: oltre quella
  soglia l'app segnala che l'elenco è parziale.
- Su AWS aggiungere e aggiornare un tag sono la **stessa** operazione (`tag_resources`
  sovrascrive la chiave se esiste): la distinzione add/update esiste solo nella UI del tag
  rapido, per far vedere prima del clic se un valore verrà sostituito.
- Il tag rapido aggiorna la tabella **in locale** invece di rileggere tutto da AWS, per restare
  immediato anche con centinaia di risorse; la cache lato server viene comunque invalidata,
  quindi il caricamento successivo mostra i dati veri.
- L'elenco letto viene tenuto in **cache in memoria** per coppia profilo/region: il pulsante
  <kbd>🔄</kbd> forza la rilettura, che avviene comunque in automatico dopo ogni modifica ai tag.
- Le API `tag_resources` e `untag_resources` accettano al massimo **20 ARN per chiamata**:
  la classe `TagManager` spezza automaticamente le liste più lunghe.
- AWS non solleva eccezioni sui singoli ARN falliti ma li restituisce in `FailedResourcesMap`:
  gli errori vengono raccolti e mostrati nella pagina.
- Non tutti i servizi AWS sono coperti dalle due API: qualcosa può comunque mancare
  rispetto alla console.
