"""
See README.md for instructions and documentation.

Esempio01_SimplePrompt: chat semplice con scelta del modello e prompt da input.
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
    "1": ("gpt-4.1",              "OpenAI GPT-4.1 (free and fast)"),
    "2": ("gpt-5.4",              "OpenAI GPT-5.4 (powerful)"),
    "3": ("claude-sonnet-4.6",    "Anthropic Claude Sonnet 4.6 (code)"),
    "4": ("gemini-3.1-pro",       "Google Gemini 3.1 Pro (multimodal)"),
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
        response = await session.send_and_wait({"prompt": prompt})
        print(estrai_testo(response))
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

if __name__ == "__main__":
    asyncio.run(main())