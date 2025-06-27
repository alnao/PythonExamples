# RobotFramework esempio 01 simple

Caratteristiche di questo esempio:
- Sito di test reale: Usa the-internet.herokuapp.com che è un sito dedicato ai test
- Credenziali valide: Username: tomsmith, Password: SuperSecretPassword!
- Test multipli: Include test positivi e negativi
- Setup e Teardown: Gestisce automaticamente apertura/chiusura browser
- Attese esplicite: Usa Wait Until Element Is Visible per maggiore stabilità
- Selettori robusti: Usa ID e CSS selectors appropriati
- Documentazione: Ogni keyword è documentata
- Tags: Per organizzare e filtrare i test

Struttura progetto
```
├── README.md                   # questo file
├── run-test.sh                 # script sh per lanciare i test
├── test.resource               # file delle risorse del robot framework
└── test.robot                  # script con i test di robot framework
```

## Installazione
Comandi per l'installazione di *RobotFramework* su server dove è già presente python3 (3.9+):
```
pip3 install --user robotframework robotframework-jsonlibrary robotframework-requests robotframework-databaselibrary boto3 kafka-python requests PyMySQL psycopg2-binary --break-system-packages
robot --outputdir robotoutput test-install.robot
```

# Esecuzione robot framework
Comando per l'esecuzione dei test Robot Framework:
```
sh run-tests.sh
```
E vedere la cartella di output `robotoutput` il risultato dei test.


# AlNao.it
Nessun contenuto in questo repository è stato creato con IA o automaticamente, tutto il codice è stato scritto con molta pazienza da Alberto Nao. Se il codice è stato preso da altri siti/progetti è sempre indicata la fonte. Per maggior informazioni visitare il sito [AlNao.it](https://www.alnao.it/).

## License
Public projects 
<a href="https://it.wikipedia.org/wiki/GNU_General_Public_License"  valign="middle"><img src="https://img.shields.io/badge/License-GNU-blue" style="height:22px;"  valign="middle"></a> 
*Free Software!*
