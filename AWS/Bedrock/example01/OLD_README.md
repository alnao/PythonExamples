
Prima controlliamo quali modelli sono disponibili nella tua regione:
aws bedrock list-foundation-models --region eu-central-1 --query "modelSummaries[?contains(modelId, 'embed')].{ModelId:modelId,Status:modelLifecycle.status}" --output table


check_model.py




a. Amazon Bedrock Console
Vai su Amazon Bedrock.
    Seleziona la regione: Frankfurt eu-central-1
    Scegli i modelli da abilitare:
        Meta Llama 3.x Instruct
        Mistral
        Titan Embeddings (per gli embedding)
    Clicca su Enable access per ciascun modello che vuoi usare.
    La richiesta viene processata in pochi minuti/ore.


3. Crea una IAM role/policy per EC2 (o Lambda, etc.)
La IAM role deve permettere:
    Invocare modelli Bedrock
    Accedere a S3 (se usi upload/backup)
    Scrivere su CloudWatch (per i log)
a. Vai su IAM → Roles
Clicca Create role.
Scegli EC2 come servizio che userà la role.
b. Allegare policy personalizzata


4. Avvia una EC2 e associa la IAM role
Avvia una istanza EC2 (Amazon Linux 2023, t3.micro o superiore).
Durante la configurazione, ASSOCIA la IAM role appena creata.
Apri le porte necessarie (22 per SSH, 8000 per FastAPI).




Certo! Ecco alcuni esempi di comandi curl per testare la tua API FastAPI su AWS Bedrock.

Supponendo che il servizio sia attivo su http://3.72.71.191:8000:


1. Health check
    curl http://3.72.71.191:8000/health
2. Ingest (carica un file di testo e lo indicizza)
    curl -X POST http://3.72.71.191:8000/ingest \
    -F "file=@document.txt" \
    -F "doc_id=mydoc1"
3. Query (cerca tra i documenti indicizzati)
    curl -X POST "http://3.72.71.191:8000/query?q=WhatIsAWSBedrock?&k=4" | jq
4. Generate (prompt diretto al modello chat)
    curl -X POST "http://3.72.71.191:8000/generate" \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Tell me about AWS Bedrock."}'
Se vuoi vedere la risposta formattata:
    curl -X POST "http://3.72.71.191:8000/query?q=WhatIsAWSBedrock?&k=4" | jq

Se hai bisogno di curl per altri endpoint o payload di esempio, chiedi pure!

