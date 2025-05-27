*** Settings ***
Library           robotLib.KafkaLibrary
Library           robotLib.DynamoLibrary
Library           JSONLibrary
Library           Collections
Library           BuiltIn

*** Variables ***
${KAFKA_TOPIC}    test.alberto
${KAFKA_SERVER}   localhost:9092
${DYNAMO_TABLE}   alberto-dy2
${DYNAMO_SERVER}  http://localhost:8000
${MESSAGE_ID}     naoRobot1800
${MESSAGE}        {"id": "${MESSAGE_ID}", "value": "test"}
${MAX_RETRIES}    5
${WAIT_SECONDS}   10

*** Test Cases ***
Send Message And Verify In DynamoDB
    [Documentation]    Invia un messaggio a Kafka e verifica che appaia in DynamoDB
    Send Kafka Message    ${KAFKA_TOPIC}    ${MESSAGE}
    Wait For DynamoDB Entry    ${MESSAGE_ID}

*** Keywords ***
Send Kafka Message
    [Arguments]    ${topic}    ${message}
    Send Message    ${topic}    ${message}    server=${KAFKA_SERVER}

Wait For DynamoDB Entry
    [Arguments]    ${id}
    FOR    ${i}    IN RANGE    ${MAX_RETRIES}
        Log    Tentativo ${i+1} di ${MAX_RETRIES}
        ${item}=    Get Item By Id    ${DYNAMO_TABLE}    ${id}
        Run Keyword If    $item is not None    Exit For Loop
        Sleep    ${WAIT_SECONDS}
    END
    Run Keyword If    $item is None    Fail    Elemento non trovato in DynamoDB dopo ${MAX_RETRIES} tentativi