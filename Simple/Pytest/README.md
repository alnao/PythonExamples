# Simple - Pytest

Esempi di test automatici con [pytest](https://docs.pytest.org/) partendo da due script già presenti nella cartella `Simple`:
- `conto.py` è la versione testabile di [conto4.py](../conto4.py) (conti correnti e bonifici)
- `expense_manager.py` è la versione testabile di [expense_manager.py](../expense_manager.py) (gestore spese a menu)

## Struttura
```
Pytest/
├── conto.py                         conti, prelievi, depositi, bonifici
├── expense_manager.py               spese, totali, filtri, salvataggio JSON, menu
├── pytest.ini                       configurazione: cartella test, pythonpath, marker
├── requirements.txt
└── tests/
    ├── conftest.py                  fixture condivise
    ├── test_conto.py
    ├── test_conto4_originale.py     test di caratterizzazione del codice originale
    └── test_expense_manager.py
```

## Da codice "da script" a codice testabile
Gli script originali stampano a video e leggono da tastiera: si possono provare solo a mano. Le versioni in questa cartella cambiano poche cose:

| Originale | Versione testabile | Perché |
|---|---|---|
| `preleva` restituisce `0` se il saldo non basta | solleva `SaldoInsufficienteError` | `0` era ambiguo: saldo azzerato o prelievo rifiutato? |
| il bonifico deposita anche se il prelievo fallisce | prima preleva, poi deposita (atomico) | nell'originale si creavano soldi dal nulla |
| importi `float` | importi `Decimal` | `0.1 + 0.1 + 0.1` con i float non fa `0.3` |
| `view()` e `total()` stampano | `elenco()` e `totale()` restituiscono valori | un valore si confronta con `assert`, una stampa no |
| logica e menu nella stessa classe | `GestoreSpese` separato da `main()` | la logica si testa senza simulare la tastiera |
| `Expense` accetta qualsiasi valore | `Spesa` è una dataclass che valida i dati | gli errori emergono alla creazione, non dopo |

## Cosa mostrano i test
- **fixture** (`conftest.py`): oggetti pronti iniettati per nome nei test, compresa una fixture *factory* (`crea_spesa`) e una fixture che ne usa un'altra
- **`@pytest.mark.parametrize`**: lo stesso test eseguito con più dati, anche con `ids` leggibili
- **`pytest.raises(..., match=...)`**: verifica che venga sollevata l'eccezione giusta con il messaggio giusto
- **`pytest.approx`**: confronto tra float con tolleranza
- **`tmp_path`**: cartella temporanea per testare il salvataggio su file
- **`monkeypatch`**: sostituisce `input()` per simulare l'utente al menu e la funzione `oggi()` per fissare la data
- **`unittest.mock.patch`**: come monkeypatch, ma registra anche le chiamate (`assert_called_once`)
- **`capsys`**: cattura quello che il codice stampa
- **marker personalizzati**: `@pytest.mark.lento`, registrato in `pytest.ini`
- **`xfail(strict=True)`**: in `test_conto4_originale.py` il bug del bonifico originale è documentato come test che *deve* fallire
- **`scope="module"`** e **`pytest.skip`**: fixture eseguita una volta sola per file, salto del test se il file originale non c'è

## Comandi
Dalla cartella `Simple/Pytest`, usando il virtualenv condiviso del repository:
```bash
../../.venv/bin/pip install -r requirements.txt

../../.venv/bin/pytest                              # tutti i test
../../.venv/bin/pytest -v                           # un test per riga
../../.venv/bin/pytest -m "not lento"               # esclude i test marcati lento
../../.venv/bin/pytest -k bonifico                  # solo i test con "bonifico" nel nome
../../.venv/bin/pytest tests/test_conto.py::test_bonifico   # un singolo test
../../.venv/bin/pytest -x --lf                      # si ferma al primo errore, riparte dagli ultimi falliti
../../.venv/bin/pytest --cov=. --cov-report=term-missing    # copertura con le righe non testate
```

Risultato atteso: `62 passed, 1 xfailed`.

Gli script si possono anche eseguire direttamente:
```bash
../../.venv/bin/python conto.py
../../.venv/bin/python expense_manager.py     # salva le spese in spese.json alla chiusura
```


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

