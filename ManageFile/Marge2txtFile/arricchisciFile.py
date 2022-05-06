import csv
from datetime import datetime

rapportovuoto='    ' #mettere lunghezzaRapporti spazi
lunghezzaRapporti=4
posizioneFidoNelBAN=2
posizioneNelBan=10

#metodo che trascodifica il formato fido dal bancll a formato focus
def fidoBAN2focus(rapp):
  return rapp

#metodo che trascodifica il rapporto da formato focus a formato bancll
def rapportoFocus2BAN(rapp):
  return rapp

def arrischiFile():
  listaSistemati = {}
  fileBanFinale = ""
  #apro file per recuperare elenco legami da file focus XXXXXX
  with open("rapporti.csv") as fp:
    reader = csv.reader(fp, delimiter=";", quotechar='"')
    tuples = [tuple(row) for row in reader]
    #print (  tuples  )
    #creo un dizionario con tutti i legami tra fido e rapporto dal file focus
    dictlist= dict((a,d) for a,b,c, d in tuples)
    print ( dictlist )
    #apro il BAN
    with open("BAN.txt") as file:
      lines = file.readlines()
      for line in lines:
        line = line .replace('\n','')
        #per ogni riga recupero i rapporti fido e  
        rapportoFido=line[posizioneFidoNelBAN:posizioneFidoNelBAN+lunghezzaRapporti]
        rapportoOrig=line[posizioneNelBan:posizioneNelBan+lunghezzaRapporti]
        #se non c'è il rapporto lo cerco
        if rapportoOrig == rapportovuoto :
          rapportoNuovo=''
          try:
            # cerco rapporto  che mancava e trovato nel file focus, lo aggiungo   
            rapportoNuovo = dictlist[ fidoBAN2focus(rapportoFido) ]
            rapportoNuovo = rapportoFocus2BAN(rapportoNuovo)
            listaSistemati[rapportoFido]=rapportoNuovo
            #print ( line + 'A' + valore )
          except: #print ("non trovato")
            # exception se non l'ho trovato purtroppo vado avanti
            rapportoNuovo = rapportovuoto
          #ricostruisco la riga mettendo il rapporto nuovo e aggiunto alla file finale
          line = line[0:posizioneNelBan] + rapportoNuovo + line[posizioneNelBan+lunghezzaRapporti]
          fileBanFinale += line + "\n"
        else:
          #se c'era già rapporto lo aggiunto alla lista senza fare nulla
          fileBanFinale += line + "\n"
      #Fine ciclo for
    #Fine with open("BAN.txt")
  #Fine with open("filename.csv") 
  
  #Scrivo il file di OUTPUT
  with open('OUT.txt', 'w') as the_file:
    the_file.write(fileBanFinale)
  #print ( fileBanFinale )

  #Scrivo il file di Log
  dateTimeObj = datetime.now()
  timestampStr = dateTimeObj.strftime("%d%b%Y%H%M%S")
  with open("OUT.log", 'w') as csv_file:  
    writer = csv.writer(csv_file)
    for key, value in listaSistemati.items():
       writer.writerow([key, value])

  #print ( "Rapporti trovati :" )
  #print (listaNplSistemati)

arrischiFile()

# Vari riferimenti
#https://stackoverflow.com/questions/24662571/python-import-csv-to-list
#https://stackoverflow.com/questions/6648493/how-to-open-a-file-for-both-reading-and-writing
#https://stackoverflow.com/questions/3783530/python-tuple-to-dict
#https://stackoverflow.com/questions/17140886/how-to-search-and-replace-text-in-a-file
#https://thispointer.com/python-how-to-get-current-date-and-time-or-timestamp/
#https://stackoverflow.com/questions/8685809/writing-a-dictionary-to-a-csv-file-with-one-line-for-every-key-value

#Leggere file da S3 con lambda
#https://www.gcptutorials.com/post/how-to-read-files-from-s3-using-python-aws-lambda
#import boto3
#s3_client = boto3.client("s3")
#S3_BUCKET = 'BUCKET_NAME'
#def lambda_handler(event, context):
#  object_key = "OBJECT_KEY"  # replace object key
#  file_content = s3_client.get_object(
#      Bucket=S3_BUCKET, Key=object_key)["Body"].read()
#  print(file_content)

#Scrivere file in s3 con Py Lambda
#https://stackoverflow.com/questions/48945389/how-could-i-use-aws-lambda-to-write-file-to-s3-python
#import boto3
#def lambda_handler(event, context):
#   string = "dfghj"
#    encoded_string = string.encode("utf-8")
#
#    bucket_name = "s3bucket"
#    file_name = "hello.txt"
#    s3_path = "100001/20180223/" + file_name
#
#    s3 = boto3.resource("s3")
#    s3.Bucket(bucket_name).put_object(Key=s3_path, Body=encoded_string