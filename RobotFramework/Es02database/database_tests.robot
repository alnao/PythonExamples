*** Settings ***
Resource            ./database.resource
Suite Setup         Setup Database
Suite Teardown      Teardown Database
Test Setup          Pulisci Tabella Utenti

*** Test Cases ***
Test Inserimento Utente
    [Documentation]    Testa l'inserimento di un nuovo utente
    [Tags]    crud    insert
    
    # Verifica che la tabella sia vuota
    ${count_iniziale}=    Conta Utenti Totali
    Should Be Equal As Numbers    ${count_iniziale}    0
    
    # Inserisce un nuovo utente
    Inserisci Utente    Mario Rossi    mario.rossi@email.com    30    1
    
    # Verifica che l'utente sia stato inserito
    ${count_finale}=    Conta Utenti Totali
    Should Be Equal As Numbers    ${count_finale}    1
    
    # Verifica i dati dell'utente
    Verifica Dati Utente    mario.rossi@email.com    Mario Rossi    30

Test Inserimento Multipli Utenti
    [Documentation]    Testa l'inserimento di più utenti
    [Tags]    crud    insert    multiple
    
    # Inserisce più utenti
    Inserisci Utente    Mario Rossi       mario.rossi@email.com      30    1
    Inserisci Utente    Anna Verdi        anna.verdi@email.com       25    1
    Inserisci Utente    Luca Bianchi      luca.bianchi@email.com     35    0
    
    # Verifica il conteggio totale
    ${count}=    Conta Utenti Totali
    Should Be Equal As Numbers    ${count}    3
    
    # Verifica utenti attivi
    ${utenti_attivi}=    Trova Utenti Attivi
    ${count_attivi}=    Get Length    ${utenti_attivi}
    Should Be Equal As Numbers    ${count_attivi}    2

Test Aggiornamento Utente
    [Documentation]    Testa l'aggiornamento di un utente esistente
    [Tags]    crud    update
    
    # Inserisce un utente
    Inserisci Utente    Mario Rossi    mario.rossi@email.com    30    1
    
    # Ottiene l'ID dell'utente
    ${id}=    Ottieni ID Utente Per Email    mario.rossi@email.com
    
    # Aggiorna l'utente
    Aggiorna Utente    ${id}    Mario Rossi Aggiornato    mario.rossi.new@email.com    35
    
    # Verifica che l'utente sia stato aggiornato
    Verifica Dati Utente    mario.rossi.new@email.com    Mario Rossi Aggiornato    35
    
    # Verifica che la vecchia email non esista più
    Verifica Utente Non Esiste    mario.rossi@email.com

Test Eliminazione Utente
    [Documentation]    Testa l'eliminazione di un utente
    [Tags]    crud    delete
    
    # Inserisce un utente
    Inserisci Utente    Mario Rossi    mario.rossi@email.com    30    1
    Verifica Utente Esiste    mario.rossi@email.com
    
    # Ottiene l'ID dell'utente
    ${id}=    Ottieni ID Utente Per Email    mario.rossi@email.com
    
    # Elimina l'utente
    Elimina Utente Per ID    ${id}
    
    # Verifica che l'utente sia stato eliminato
    Verifica Utente Non Esiste    mario.rossi@email.com
    
    # Verifica che il conteggio sia 0
    ${count}=    Conta Utenti Totali
    Should Be Equal As Numbers    ${count}    0

Test Vincolo Email Unica
    [Documentation]    Testa che non si possano inserire email duplicate
    [Tags]    constraints    validation
    
    # Inserisce il primo utente
    Inserisci Utente    Mario Rossi    mario.rossi@email.com    30    1
    
    # Tenta di inserire un utente con la stessa email
    Run Keyword And Expect Error    *    
    ...    Inserisci Utente    Anna Verdi    mario.rossi@email.com    25    1
    
    # Verifica che ci sia ancora solo un utente
    ${count}=    Conta Utenti Totali
    Should Be Equal As Numbers    ${count}    1

Test Query Semplice
    [Documentation]    Testa query semplici
    [Tags]    query
    
    # Inserisce dati di test
    Inserisci Utente    Mario Rossi      mario.rossi@email.com      30    1
    Inserisci Utente    Anna Verdi       anna.verdi@email.com       25    1
    Inserisci Utente    Luca Bianchi     luca.bianchi@email.com     35    0
    
    # Verifica conteggio utenti attivi
    ${utenti_attivi}=    Trova Utenti Attivi
    ${count_attivi}=    Get Length    ${utenti_attivi}
    Should Be Equal As Numbers    ${count_attivi}    2
    
    # Verifica conteggio totale
    ${count_totale}=    Conta Utenti Totali
    Should Be Equal As Numbers    ${count_totale}    3

*** Keywords ***
Setup Database
    [Documentation]    Setup iniziale del database per la suite di test
    Connetti Al Database MySQL
    Crea Tabella Utenti

Teardown Database
    [Documentation]    Cleanup finale del database
    Elimina Tabella Utenti
    Disconnetti Dal Database