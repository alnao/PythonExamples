# Verifica che i tre modelli Bedrock configurati in .env (o i default) rispondano.
# Eseguire con: python check_model.py   (servono credenziali AWS; ogni prova costa frazioni di centesimo)

from backend import settings, embed_one, chat, bedrock, converse_text

checks = {
    f"embedding ({settings.EMBEDDING_MODEL})": lambda: f"{len(embed_one('Hello world'))} dimensioni",
    f"chat ({settings.CHAT_MODEL})": lambda: chat("Rispondi solo con la parola OK."),
    f"immagini ({settings.IMAGE_MODEL})": lambda: converse_text(bedrock.converse(
        modelId=settings.IMAGE_MODEL,
        messages=[{"role": "user", "content": [{"text": "Rispondi solo con la parola OK."}]}],
        inferenceConfig={"maxTokens": 2000},
    )),
}
if not settings.IMAGE_MODEL.strip():
    checks.pop(f"immagini ({settings.IMAGE_MODEL})")  # OCR locale, nessun modello da provare

print(f"Region: {settings.AWS_REGION}")
for name, check in checks.items():
    try:
        print(f"✅ {name}: {check()}")
    except Exception as e:
        print(f"❌ {name}: {e}")
