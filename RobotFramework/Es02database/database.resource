*** Settings ***
Library    DatabaseLibrary
Library    Collections

*** Variables ***
${DB_MODULE}        pymysql
${DB_NAME}          test_db
${DB_USER}          test_user
${DB_PASSWORD}      test_password
${DB_HOST}          localhost
${DB_PORT}          3306

*** Keywords ***
Connetti Al Database MySQL
    [Documentation]    Stabilisce connessione al database MySQL
    Connect To Database    ${DB_MODULE}    ${DB_NAME}    ${DB_USER}    ${DB_PASSWORD}    ${DB_HOST}    ${DB_PORT}

Disconnetti Dal Database
    [Documentation]    Chiude la connessione al database
    Disconnect From Database

Crea Tabella Utenti
    [Documentation]    Crea la tabella utenti per i test
    Execute Sql String    CREATE TABLE IF NOT EXISTS utenti (id INT AUTO_INCREMENT PRIMARY KEY, nome VARCHAR(50) NOT NULL, email VARCHAR(100) UNIQUE NOT NULL, eta INT, attivo BOOLEAN DEFAULT TRUE, data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP);

Pulisci Tabella Utenti
    [Documentation]    Elimina tutti i record dalla tabella utenti
    Execute Sql String    DELETE FROM utenti;
    Execute Sql String    ALTER TABLE utenti AUTO_INCREMENT = 1;

Elimina Tabella Utenti
    [Documentation]    Elimina completamente la tabella utenti
    Execute Sql String    DROP TABLE IF EXISTS utenti;

Inserisci Utente
    [Arguments]    ${nome}    ${email}    ${eta}    ${attivo}=1
    [Documentation]    Inserisce un nuovo utente nel database
    Execute Sql String    INSERT INTO utenti (nome, email, eta, attivo) VALUES ('${nome}', '${email}', ${eta}, ${attivo});

Aggiorna Utente
    [Arguments]    ${id}    ${nome}    ${email}    ${eta}
    [Documentation]    Aggiorna i dati di un utente esistente
    Execute Sql String    UPDATE utenti SET nome='${nome}', email='${email}', eta=${eta} WHERE id=${id};

Elimina Utente Per ID
    [Arguments]    ${id}
    [Documentation]    Elimina un utente dal database tramite ID
    Execute Sql String    DELETE FROM utenti WHERE id=${id};

Conta Utenti Totali
    [Documentation]    Restituisce il numero totale di utenti
    ${result}=    Query    SELECT COUNT(*) as totale FROM utenti;
    Log    Risultato query count: ${result}
    ${count}=    Get From List    ${result[0]}    0
    RETURN    ${count}

Trova Utente Per Email
    [Arguments]    ${email}
    [Documentation]    Cerca un utente tramite email
    ${result}=    Query    SELECT id, nome, email, eta, attivo FROM utenti WHERE email='${email}';
    Log    Risultato query utente: ${result}
    RETURN    ${result}

Trova Utenti Attivi
    [Documentation]    Restituisce tutti gli utenti attivi
    ${result}=    Query    SELECT id, nome, email, eta, attivo FROM utenti WHERE attivo=1;
    RETURN    ${result}

Verifica Utente Esiste
    [Arguments]    ${email}
    [Documentation]    Verifica se un utente esiste nel database
    ${result}=    Trova Utente Per Email    ${email}
    ${count}=    Get Length    ${result}
    Should Be True    ${count} > 0    Utente con email ${email} non trovato

Verifica Utente Non Esiste
    [Arguments]    ${email}
    [Documentation]    Verifica che un utente non esista nel database
    ${result}=    Trova Utente Per Email    ${email}
    ${count}=    Get Length    ${result}
    Should Be Equal As Numbers    ${count}    0    Utente con email ${email} esiste ancora

Verifica Dati Utente
    [Arguments]    ${email}    ${nome_atteso}    ${eta_attesa}
    [Documentation]    Verifica che i dati dell'utente siano corretti
    ${result}=    Trova Utente Per Email    ${email}
    Should Not Be Empty    ${result}    Utente non trovato
    ${utente}=    Get From List    ${result}    0
    Log    Dati utente trovato: ${utente}
    # Accesso ai dati come tupla (indice numerico)
    ${nome_db}=    Get From List    ${utente}    1
    ${eta_db}=    Get From List    ${utente}    3
    Should Be Equal    ${nome_db}    ${nome_atteso}
    Should Be Equal As Numbers    ${eta_db}    ${eta_attesa}

Ottieni ID Utente Per Email
    [Arguments]    ${email}
    [Documentation]    Ottiene l'ID di un utente tramite email
    ${result}=    Trova Utente Per Email    ${email}
    Should Not Be Empty    ${result}    Utente non trovato
    ${utente}=    Get From List    ${result}    0
    ${id}=    Get From List    ${utente}    0
    RETURN    ${id}