# Spark by alNao
Elenco esempi:
- 01first
- 02dataFrame
- 03fistProject
- 04dataFrameReadProcessWrite

## Installazione di pySpark
- su piattaforma windows
    1) installare java (8 o 11, la 17 e successive non funzionano)
    2) installare python (3.6+)
    3) scaricare "hadoop winutils" python da `https://github.com/cdarlint/winutils`
    4) configurare le variabili d'ambiente `HADOOP_HOME` (senza bin) e `PATH` (con la bin del punto precedente) 
    5) scaricare spark da https://spark.apache.org/downloads.html
    6) configurare le variabili d'ambiente `SPARK_HOME` (senza bin) e `PATH` (con la bin del punto precedente) 
    7) testare lanciando il comando da riga di comando `pyspark`
    8) configurare le variabili d'ambiente `PYSPARK_PYTHON` e `PYSPARK_DRIVER_PYTHON` con il path dell'eseguibile py oppure vedere sotto
- su piattaforma GNU Linux , see https://www.machinelearningplus.com/pyspark/install-pyspark-on-linux/
    1) installare java (8 o 11, la 17 funziona dalla versione 3.5.1 di spark)
        pacchetto debian "openjdk" alla versione 17 (vedi https://issues.apache.org/jira/browse/SPARK-33772)
    2) installare python (3.6+)
        pacchetto python e pip
        `pip install pyspark --break-system-packages`
    3) installare spark
        ```
        wget https://archive.apache.org/dist/spark/spark-3.5.1/spark-3.5.1-bin-hadoop3.tgz
        tar -xvzf spark-3.5.1-bin-hadoop3.tgz
        sudo mv spark-3.5.1-bin-hadoop3 /opt/spark351
        sudo chmod 777 /opt/spark351
        ```
    4) configurare variabili ambiente
        `pico ~/.bashrc`
            ```
            export SPARK_HOME=/opt/spark351
            export PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin
            ```
        `source ~/.bashrc`
    5) testare comando `$ pyspark` e lanciare lo script `01first.py`

### Configurazioni variabili
Su windows vedere https://stackoverflow.com/questions/55559763/spark-not-executing-tasks
```
import os
os.environ['PYSPARK_PYTHON'] = 'C:\\ProgrammiDev\\Python311\\python.exe' # Worker executable
os.environ['PYSPARK_DRIVER_PYTHON'] = 'C:\\ProgrammiDev\\Python311\\python.exe' # Driver executable
```


## Changelog
| Data | Modifica |
|------|----------|
| 2026-11-17 | Aggiunta la sezione Changelog |


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

