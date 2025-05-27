*** Settings ***
Library    Collections
Library    JSONLibrary

*** Test Cases ***
Test Installation
    [Documentation]    Test che Robot Framework funzioni correttamente
    Log    Robot Framework installato correttamente!
    ${list}=    Create List    1    2    3
    Length Should Be    ${list}    3
    
Test JSON Library
    [Documentation]    Test della libreria JSON
    ${json_string}=    Set Variable    {"name": "test", "value": 123}
    ${json_object}=    Convert String To Json    ${json_string}
    Should Be Equal    ${json_object}[name]    test