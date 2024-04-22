# on debian 12:
# apt install libespeak-ng-libespeak-dev espeak
# pip install pyttsx3 --break-system-package
# pip install 'PyPDF2<3.0' --break-system-package
# only on Windows pip install comtypes --break-system-package for speaker = pyttsx3.init("sapi5")

import pyttsx3,PyPDF2

#from https://prateeksrivastav598.medium.com/text-to-speech-with-python-a-guide-to-using-pyttsx3-417f5787bb0f
def simple_speaker(text):
    # Initialize the TTS engine
    speaker = pyttsx3.init()
    change_voice(speaker, ITALIAN_LANGUAGE_CODE)
    # Set properties (optional)
    speaker.setProperty('rate', 150)  # Speed of speech (words per minute)
    speaker.setProperty('volume', 1.0)  # Volume (0.0 to 1.0)
    # Convert text to speech and play it
    speaker.say(text)
    # Wait for the speech to finish
    speaker.runAndWait()
    speaker.stop()

##python-pdf-audo   #from https://github.com/TiffinTech/python-pdf-audo/blob/main/main.py
def mp3_from_pdf(pdf_path,mp3_path):
    #insert name of your pdf 
    pdfreader = PyPDF2.PdfFileReader(open(pdf_path, 'rb'))
    speaker = pyttsx3.init() #"sapi5"
    #voices = speaker.getProperty("voices")[0]
    #speaker.setProperty('voice', voices)
    for page_num in range(pdfreader.numPages):
        text = pdfreader.getPage(page_num).extractText()
        clean_text = text.strip().replace('\n', ' ')
        print(clean_text)
        if len(clean_text.replace(" ",""))>0:
            speaker.save_to_file(str(clean_text), mp3_path.replace(".mp3","_page"+str(page_num)+".mp3") )
            speaker.runAndWait()

#see https://puneet166.medium.com/how-to-added-more-speakers-and-voices-in-pyttsx3-offline-text-to-speech-812c83d14c13
def get_voices():
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    for voice in voices:
        print(voice, voice.id)
        engine.setProperty('voice', voice.id)
        engine.say("Hello World!")
        engine.runAndWait()
        engine.stop()
    # get_voices()
    #<Voice id=italian          name=italian          languages=[b'\x05it']          gender=male          age=None> italian
def change_voice(engine, language, gender='VoiceGenderFemale'):
    for voice in engine.getProperty('voices'):
        if language in voice.languages: # and gender == voice.gender:
            engine.setProperty('voice', voice.id)
            return True
    raise RuntimeError("Language '{}' for gender '{}' not found".format(language, ""))

ITALIAN_LANGUAGE_CODE=b'\x05it'

if __name__ == "__main__":
    print('AlNao Python Example - Speaker')
    text=input("Insert text (empty to skip): ")
    if len(text)>0:
        simple_speaker(text)
    else:
        print("Nothing to say!")

    #
    #pdf_path = "file.pdf"
    #mp3_path = 'story.mp3'
    #mp3_from_pdf(pdf_path,mp3_path)
