"""
TODO: Aggiungere esempi di:
- Conversazione multi-turno (la sessione mantiene la storia)
- Agent con tool personalizzato (definito con @define_tool e Pydantic)
- Streaming (risposta in tempo reale con event listener)
"""

"""
GitHub Copilot SDK — Esempio Python
=============================================

AUTENTICAZIONE (scegli UNO dei metodi) nella Copilot-CLI o direttamente nel codice:
    Metodo 1 (consigliato): Autenticati via CLI una volta sola
        copilot -i "login"
    Metodo 2: Passa un GitHub token direttamente nel codice
        CopilotClient({"github_token": "ghp_xxxx..."})
        
    Metodo 3: Variabile d'ambiente
        export COPILOT_GITHUB_TOKEN="il_tuo_fine_grained_token"
            Vai su GitHub.com e clicca sulla tua foto profilo in alto a destra.
            Seleziona Settings (Impostazioni).
            Nel menu a sinistra, scorri fino in fondo e clicca su Developer settings.
            Clicca su Personal access tokens e poi seleziona Fine-grained tokens.
            Clicca sul pulsante Generate new token.

INSTALLAZIONE:
    pip install github-copilot-sdk
    # Il Copilot CLI deve essere nel PATH:
    # https://docs.github.com/en/copilot/github-copilot-in-the-cli
"""


import asyncio
import os
import sys
from copilot import CopilotClient, PermissionHandler
from copilot.tools import define_tool
from pydantic import BaseModel, Field


def estrai_testo(response) -> str:
    """
    Estrae il testo da un SessionEvent.
    send_and_wait() ritorna un SessionEvent con il testo in .data.content
    (NON in .text — errore comune!)
    """
    if response is None:
        return "(nessuna risposta)"
    if hasattr(response, "data") and hasattr(response.data, "content"):
        return response.data.content
    return str(response)


# ─────────────────────────────────────────────────────────────────
# A) CHAT SEMPLICE
#    L'utente sceglie il modello e inserisce il prompt
# ─────────────────────────────────────────────────────────────────

# Modelli disponibili su GitHub Copilot (aggiorna in base al tuo piano)
MODELLI_DISPONIBILI = {
    "1": ("gpt-4.1",              "OpenAI GPT-4.1          — general purpose, veloce"),
    "2": ("gpt-5.4",              "OpenAI GPT-5.4          — più potente, più lento"),
    "3": ("claude-sonnet-4.6",    "Anthropic Claude Sonnet 4.6 — ottimo per codice e ragionamento"),
    "4": ("gemini-3.1-pro",       "Google Gemini 3.1 Pro   — multimodale, Preview"),
}

def scegli_modello() -> str:
    """Mostra un menu interattivo e restituisce il model ID scelto."""
    print("\n┌─────────────────────────────────────────────────────┐")
    print("│  Scegli il modello:                                 │")
    print("├─────────────────────────────────────────────────────┤")
    for num, (model_id, descrizione) in MODELLI_DISPONIBILI.items():
        print(f"│  [{num}] {descrizione:<47}│")
    print("└─────────────────────────────────────────────────────┘")

    while True:
        scelta = input("Inserisci il numero del modello (default 1): ").strip()
        if scelta == "" :
            scelta = "1"  # default
        if scelta in MODELLI_DISPONIBILI:
            model_id, descrizione = MODELLI_DISPONIBILI[scelta]
            print(f"✅ Modello selezionato: {model_id}\n")
            return model_id
        print(f"⚠️  Scelta non valida. Inserisci un numero tra 1 e {len(MODELLI_DISPONIBILI)}.")

async def demo_chat_semplice():
    print("\n" + "=" * 60)
    print("  A) CHAT SEMPLICE")
    print("=" * 60)

    # Selezione interattiva del modello
    model_id = scegli_modello()

    # Input del prompt da parte dell'utente
    print("💬 Inserisci il tuo prompt (invio per confermare):")
    prompt = input("👤 > ").strip()
    if not prompt:
        print("⚠️  Nessun prompt inserito, uso un testo di esempio.")
        prompt = "Spiega in 3 righe cosa fa il pattern Repository in Python."

    client = CopilotClient()
    await client.start()

    try:
        session = await client.create_session({
            "model": model_id,
            "on_permission_request": PermissionHandler.approve_all,
        })

        print(f"\n🤖 Risposta da [{model_id}]:\n")
        # ✅ Il testo è in response.data.content, non in response.text
        response = await session.send_and_wait({"prompt": prompt})
        print(estrai_testo(response))
    finally:
        await client.stop()


# ─────────────────────────────────────────────────────────────────
# B) CONVERSAZIONE MULTI-TURNO
#    La sessione mantiene automaticamente la storia del dialogo
# ─────────────────────────────────────────────────────────────────
async def demo_multi_turno():
    print("\n" + "=" * 60)
    print("  B) CONVERSAZIONE MULTI-TURNO")
    print("=" * 60)

    client = CopilotClient()
    await client.start()

    try:
        session = await client.create_session({
            "model": "gpt-4o",
            "on_permission_request": PermissionHandler.approve_all,
        })

        domande = [
            "Cos'è un decoratore in Python? Spiegalo brevemente.",
            "Puoi darmi un esempio pratico di quello che hai appena spiegato?",
            "Come lo modificheresti per supportare argomenti opzionali?",
        ]

        for i, domanda in enumerate(domande, 1):
            print(f"\n👤 Turno {i}: {domanda}")
            response = await session.send_and_wait({"prompt": domanda})
            print(f"🤖 Risposta:\n{estrai_testo(response)}")
            print("-" * 40)
    finally:
        await client.stop()


# ─────────────────────────────────────────────────────────────────
# C) AGENT CON TOOL PERSONALIZZATO
#    Definiamo un tool con @define_tool e Pydantic per i parametri
# ─────────────────────────────────────────────────────────────────

TICKET_DB = {
    "TICKET-001": {"titolo": "App crash al login",            "stato": "aperto",          "priorità": "alta"},
    "TICKET-002": {"titolo": "Bottone Salva rotto su Safari",  "stato": "in lavorazione",  "priorità": "media"},
    "TICKET-003": {"titolo": "Aggiorna dipendenze Python",     "stato": "chiuso",          "priorità": "bassa"},
}

class CercaTicketParams(BaseModel):
    ticket_id: str = Field(description="ID del ticket, es. TICKET-001")

@define_tool(description="Cerca un ticket nel sistema interno. Restituisce stato e priorità.")
async def cerca_ticket(params: CercaTicketParams) -> dict:
    tid = params.ticket_id.upper()
    if tid in TICKET_DB:
        d = TICKET_DB[tid]
        return {
            "trovato": True,
            "id": tid,
            "titolo": d["titolo"],
            "stato": d["stato"],
            "priorità": d["priorità"],
        }
    return {"trovato": False, "id": tid, "messaggio": "Ticket non trovato"}

async def demo_agent_con_tool():
    print("\n" + "=" * 60)
    print("  C) AGENT CON TOOL PERSONALIZZATO")
    print("=" * 60)

    client = CopilotClient()
    await client.start()

    try:
        session = await client.create_session({
            "model": "gpt-4o",
            "on_permission_request": PermissionHandler.approve_all,
            "tools": [cerca_ticket],
        })

        richieste = [
            "Controlla lo stato del ticket TICKET-002 e dimmi se è urgente.",
            "Esiste il ticket TICKET-999?",
            "Quali ticket ha senso affrontare per primi tra TICKET-001 e TICKET-003?",
        ]

        for richiesta in richieste:
            print(f"\n👤 Richiesta: {richiesta}")
            response = await session.send_and_wait({"prompt": richiesta})
            print(f"🤖 Risposta:\n{estrai_testo(response)}")
            print("-" * 40)
    finally:
        await client.stop()


# ─────────────────────────────────────────────────────────────────
# D) STREAMING — risposta in tempo reale con event listener
# ─────────────────────────────────────────────────────────────────
async def demo_streaming():
    print("\n" + "=" * 60)
    print("  D) RISPOSTA IN STREAMING")
    print("=" * 60)

    client = CopilotClient()
    await client.start()

    try:
        session = await client.create_session({
            "model": "gpt-4o",
            "on_permission_request": PermissionHandler.approve_all,
            "streaming": True,
        })

        done = asyncio.Event()

        def on_event(event):
            event_type = event.type.value if hasattr(event.type, "value") else str(event.type)

            if event_type == "assistant.message_delta":
                # Chunk di testo in arrivo — stampa subito senza newline
                delta = getattr(event.data, "delta_content", None) or ""
                sys.stdout.write(delta)
                sys.stdout.flush()

            elif event_type == "assistant.message":
                # Messaggio finale completo (sempre emesso anche in streaming)
                print()  # a capo dopo il testo streamato

            elif event_type == "session.idle":
                done.set()

            elif event_type == "error":
                print(f"\n❌ Errore: {event.data}")
                done.set()

        session.on(on_event)

        print("🤖 Risposta (streaming):\n")
        await session.send({"prompt": "Scrivi un breve haiku sul codice Python."})
        await done.wait()

    finally:
        await client.stop()


# ─────────────────────────────────────────────────────────────────
# E) BYOK — usa la tua chiave OpenAI senza abbonamento Copilot
# ─────────────────────────────────────────────────────────────────
async def demo_byok_openai():
    print("\n" + "=" * 60)
    print("  E) BYOK — Chiave OpenAI propria")
    print("=" * 60)

    client = CopilotClient({
        "provider": {
            "type": "openai",
            "api_key": os.environ.get("OPENAI_API_KEY", "sk-..."),
        }
    })
    await client.start()

    try:
        session = await client.create_session({
            "model": "gpt-4o",
            "on_permission_request": PermissionHandler.approve_all,
        })
        response = await session.send_and_wait({
            "prompt": "Dimmi 3 motivi per usare dataclasses in Python."
        })
        print(f"🤖 Risposta:\n{estrai_testo(response)}")
    finally:
        await client.stop()


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────
async def main():
    print("╔══════════════════════════════════════════════════════╗")
    print("║     GitHub Copilot SDK — Esempi Python               ║")
    print("╚══════════════════════════════════════════════════════╝")

    # Decommenta le demo che vuoi eseguire:
    await demo_chat_semplice()
    # await demo_multi_turno()
    # await demo_agent_con_tool()
    # await demo_streaming()
    # await demo_byok_openai()


if __name__ == "__main__":
    asyncio.run(main())