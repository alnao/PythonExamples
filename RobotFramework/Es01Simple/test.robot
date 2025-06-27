*** Settings ***
Resource    ./test.resource
Test Setup    Apri Browser E Vai Alla Pagina Di Login
Test Teardown    Chiudi Browser

*** Test Cases ***
Test Login Con Credenziali Valide
    [Documentation]    Testa il login con username e password corretti
    [Tags]    login    positive
    Inserisci Credenziali    tomsmith    SuperSecretPassword!
    Clicca Pulsante Login
    Verifica Login Riuscito

Test Login Con Username Sbagliato
    [Documentation]    Testa il login con username errato
    [Tags]    login    negative
    Inserisci Credenziali    utente_sbagliato    SuperSecretPassword!
    Clicca Pulsante Login
    Verifica Login Fallito

Test Login Con Password Sbagliata
    [Documentation]    Testa il login con password errata
    [Tags]    login    negative
    Inserisci Credenziali    tomsmith    password_sbagliata
    Clicca Pulsante Login
    Verifica Login Fallito

Test Login Con Campi Vuoti
    [Documentation]    Testa il login senza inserire credenziali
    [Tags]    login    negative
    Inserisci Credenziali    ${EMPTY}    ${EMPTY}
    Clicca Pulsante Login
    Verifica Login Fallito