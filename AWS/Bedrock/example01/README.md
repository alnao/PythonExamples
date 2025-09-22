



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






