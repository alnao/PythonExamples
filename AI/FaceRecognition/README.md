# Face Recognition Photo Analyzer — Desktop & Web Application

Applicazione Python avanzata per analizzare cartelle di foto, identificare persone con riconoscimento facciale, memorizzare la cronologia ed esplorare le immagini con un'interfaccia moderna disponibile sia in versione **Desktop (CustomTkinter)** che **Web (Flask + Bootstrap 5)**.

## 🚀 Caratteristiche Principali

- **🌐 Versione Web (Flask + Bootstrap 5 Dark)**: Interfaccia Web SPA responsive con anteprima immagini, Live Progress Bar, selettore dimensione foto e modal ingranditi.
- **🖥️ Versione Desktop GUI (CustomTkinter)**: Interfaccia grafica nativa desktop basata sulla palette Bootstrap Dark.
- **⚡ Cache SQLite & Multithreading**: Risultati istantanei per cartelle già analizzate e caricamento griglia asincrono in background.
- **📁 Selezione Cartella Nativa**: Integrazione diretta con il dialogo nativo di sistema.
- **🔁 Ricerca Ricorsiva**: Flag per analizzare anche tutte le sottocartelle della cartella selezionata (interruttore *"Includi sottocartelle"* nella web app, checkbox *"🔁 Sottocartelle"* nella GUI desktop). Le cartelle nascoste sono escluse; il flag è memorizzato per ogni scansione e mostrato nella dashboard dei job.
- **📜 Cronologia Ricerche Passate**: Database SQLite per riaprire o consultare in 1-click cartelle già analizzate.

## 🔍 Come funziona il riconoscimento

1. **Rilevamento** (`detect_faces`): ogni immagine viene aperta con Pillow applicando l'orientamento EXIF — `face_recognition.load_image_file()` lo ignora, quindi le foto ruotate da smartphone venivano analizzate coricate e i volti non venivano trovati. Le immagini molto grandi sono ridotte a 2000px per il rilevamento e le coordinate dei volti riportate alla risoluzione piena; se il primo passaggio non trova nulla si ritenta con `upsample=2` per i volti piccoli o lontani.
2. **Clustering** (`cluster_faces`): passata greedy + fasi di *merge* e *riassegnazione*, così il risultato non dipende più dall'ordine di scansione e la stessa persona non si spezza in più gruppi per pose e luci diverse.
3. **Metrica**: la distanza fra un volto e un gruppo è la media dei **k=3 vicini più prossimi**. La soglia 0.6 di `face_recognition` è tarata su coppie di volti: la media su *tutti* i membri di un cluster scartava match veri, il minimo puro incatenava persone diverse.
4. **Categorizzazione** (`categorize_photos`): riusa gli insiemi di foto calcolati durante il clustering (`match_paths`), quindi la scheda *"Senza Persona"* è esattamente il complemento del volto selezionato nella sidebar — i due conteggi non possono più divergere. Prima si confrontava la media (centroide) del cluster con una soglia tarata su coppie, ottenendo liste incoerenti.

> ⚠️ La cache SQLite ha un campo `algo_version`: le foto analizzate con la versione precedente vengono rianalizzate automaticamente alla prima scansione (una sola volta per cartella). Le immagini nuove sono elaborate in **processi paralleli** (dlib non è thread-safe ma è process-safe): ~4x più veloce sulla prima scansione.

## 🛠️ Esecuzione

Attiva l'ambiente virtuale prima di lanciare l'app:

```bash
source /mnt/Dati4/Workspace/PythonExamples/.venv/bin/activate
cd AI/FaceRecognition/
```

### 🌐 Avvio Versione Web (Consigliato)
```bash
python app.py
```
*Si aprirà automaticamente il browser su `http://127.0.0.1:5000`.*

### 🖥️ Avvio Versione Desktop GUI
```bash
python main.py
```

## 📁 Struttura del Progetto

| File | Descrizione |
|------|-------------|
| `app.py` | Backend Flask Web App e REST API |
| `main.py` | Interfaccia Desktop GUI (CustomTkinter) |
| `face_analyzer.py` | Logica di rilevamento volti, clustering e categorizzazione parallela |
| `face_cache.py` | Engine di caching SQLite per encodings biometrici e cronologia scansioni |
| `templates/index.html` | UI Single-Page HTML5 / Bootstrap 5 |
| `static/js/main.js` | Client JavaScript (polling, grid, tabs, modal navigation) |
| `static/css/style.css` | Stili custom Bootstrap Dark Theme |
| `requirements.txt` | Dipendenze del progetto |







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


