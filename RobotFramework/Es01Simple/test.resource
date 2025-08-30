*** Settings ***
Library     SeleniumLibrary

*** Variables ***
${BROWSER}          Chrome
${URL}              http://the-internet.herokuapp.com/login
${USERNAME_FIELD}   id=username
${PASSWORD_FIELD}   id=password
${LOGIN_BUTTON}     css=button[type="submit"]
${SUCCESS_MESSAGE}  css=.flash.success
${ERROR_MESSAGE}    css=.flash.error

*** Keywords ***
Apri Browser E Vai Alla Pagina Di Login
    [Documentation]    Apre il browser e naviga alla pagina di login
    Open Browser    ${URL}    ${BROWSER}
    Maximize Browser Window
    Set Selenium Speed    0.5s

Inserisci Credenziali
    [Arguments]    ${username}    ${password}
    [Documentation]    Inserisce username e password nei campi appropriati
    Wait Until Element Is Visible    ${USERNAME_FIELD}    10s
    Input Text    ${USERNAME_FIELD}    ${username}
    Input Text    ${PASSWORD_FIELD}    ${password}

Clicca Pulsante Login
    [Documentation]    Clicca il pulsante di login
    Click Button    ${LOGIN_BUTTON}

Verifica Login Riuscito
    [Documentation]    Verifica che il login sia andato a buon fine
    Wait Until Element Is Visible    ${SUCCESS_MESSAGE}    10s
    Element Should Contain    ${SUCCESS_MESSAGE}    You logged into a secure area!

Verifica Login Fallito
    [Documentation]    Verifica che il login sia fallito
    Wait Until Element Is Visible    ${ERROR_MESSAGE}    10s
    Element Should Be Visible    ${ERROR_MESSAGE}

Chiudi Browser
    [Documentation]    Chiude il browser
    Close Browser