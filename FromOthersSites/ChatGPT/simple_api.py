import openai
import os
#pip install openai
#in debian 12: "pip install openai --break-system-packages" #see #https://stackoverflow.com/questions/75608323/how-do-i-solve-error-externally-managed-environment-everytime-i-use-pip3

#to run
#export OPENAI_API_KEY=valore
openai.api_key= os.getenv("OPENAI_API_KEY") #NOOOOO openai.api_key="aaaaaaaa"

def test_api():
    risposta=openai.Completion.create(
        engine="text-davinci-002",
        prompt="Chi ha scoperto l'america?",
        max_tokens=1,
        n=1,
        stop=None,
        tempperature=0.9,
    )
    print(risposta)

def create_conv_simple():
    response=openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role":"user","content":"Chi ha scoperto l'america"}
        ],
    )
    return response.choises[0].message.content

def create_conv_multiple(chat_history,message):
    chat_history.append({"role":"user","content":message,})
    response=openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=chat_history,
    )
    assistant_response=response.choises[0].message.content
    chat_history.append( {"role":"assistant","content":assistant_response } )
    return chat_history,assistant_response

if __name__ == "__main__":
    print('text_api')
    #test_api()
    #v=create_conv_simple()
    #print(v)
    initial=[]
    initial.append({"role":"system","content":"Usa un tono da teenager."})
    hist,risp=create_conv_multiple(initial, "Quale è il capoluogo della Toscana?")
    print(risp)
    hist,risp=create_conv_multiple(hist, "Quanti abitanti ha?")
    print(risp)

