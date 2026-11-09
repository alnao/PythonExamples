# Simple - GuiTextual

Esempi di [Textual](https://textual.textualize.io/): applicazioni con interfaccia grafica **dentro il terminale**, con mouse, colori, temi, finestre modali e fogli di stile simili al CSS. Funzionano anche via SSH, senza server grafico.

È l'evoluzione delle librerie per terminale già presenti in [Simple/Gui](../Gui/) (urwid, pyTermTk, pythondialog).

## Esempi
| File | Contenuto |
|---|---|
| `ciao.py` | prima applicazione: `compose()`, widget `Header`, `Footer`, `Button`, `Digits`, eventi dei pulsanti, tasti rapidi (`BINDINGS` e metodi `action_*`), variabile `reactive` con `watch_*`, notifiche, cambio tema, CSS scritto nella classe |
| `spese.py` + `spese.tcss` | il [gestore spese](../expense_manager.py) con interfaccia completa: modulo con `Input` validati (`Function`, `Number`), `Select` delle categorie, `DataTable` ordinata, finestra modale di conferma (`ModalScreen`) che restituisce un valore, riepilogo per categoria aggiornato in automatico, salvataggio JSON, stile in un file `.tcss` separato |
| `test_spese.py` | test automatici con `run_test()` e `Pilot`: clic, tasti digitati, validazione, conferma ed eliminazione, salvataggio |

## Concetti principali
- **compose**: descrive l'albero dei widget con `yield`; i container (`Horizontal`, `Vertical`, `VerticalScroll`, `Center`) si usano con `with`
- **CSS di Textual (TCSS)**: dimensioni in celle del terminale, `1fr` per lo spazio rimanente, variabili di tema (`$primary`, `$accent`, `$error`) che cambiano con il tema chiaro/scuro
- **eventi**: metodi `on_<widget>_<evento>` oppure il decoratore `@on(Button.Pressed, "#id")`; lo stesso metodo può rispondere a più eventi
- **reactive**: assegnando un nuovo valore Textual chiama `watch_<nome>`, che aggiorna la grafica. Con le liste serve assegnarne una nuova (`self.spese = [*self.spese, nuova]`): modificarla sul posto con `append` non fa scattare l'aggiornamento
- **schermate modali**: `push_screen(schermata, callback)` e `dismiss(valore)` per ricevere la risposta
- **palette dei comandi**: `Ctrl+P` apre la ricerca di tutti i comandi disponibili, compreso il cambio tema

## Comandi
Dalla cartella `Simple/GuiTextual`:
```bash
../../.venv/bin/pip install -r requirements.txt
../../.venv/bin/python ciao.py
../../.venv/bin/python spese.py                 # usa spese.json in questa cartella
../../.venv/bin/python spese.py /tmp/casa.json  # oppure un altro file
../../.venv/bin/pytest test_spese.py -v         # 7 test
```

Tasti di `spese.py`:
| Tasto | Azione |
|---|---|
| `Tab` / mouse | spostarsi tra campi, tabella e pulsanti |
| `Invio` in un campo | aggiunge la spesa |
| `Canc` sulla tabella | elimina la riga selezionata (con conferma) |
| `Ctrl+S` | salva |
| `Ctrl+T` | tema chiaro/scuro |
| `Ctrl+Q` | salva ed esce |

## Strumenti di sviluppo
Con il pacchetto `textual-dev` si ha una console di debug e il ricaricamento automatico del CSS:
```bash
../../.venv/bin/pip install textual-dev
../../.venv/bin/textual console                     # in un terminale: mostra log e print dell'app
../../.venv/bin/textual run --dev spese.py          # in un altro: modifiche a spese.tcss applicate al volo
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

