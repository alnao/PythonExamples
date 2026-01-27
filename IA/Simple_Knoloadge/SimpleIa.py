# from https://www.youtube.com/watch?v=CkkjXTER2KE
# create SimpleIA_knowladge.json

import json
from difflib import get_close_matches
import os
dirname=os.path.dirname(__file__)

def print_hi(name):
    print(f'Hi, {name}!')

def load_knowledge(file_path: str) -> dict:
    with open(file_path, 'r') as f:
        data:dict = json.load(f)
    return data

def save_knowledge(file_path: str, data: dict):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

def find_best_match(user_question:str,questions:list) :
    best_match = get_close_matches(user_question, questions)
    if best_match:
        return best_match[0]
    else:
        return None

def get_answer_for_question(question:str,knowladge_base :dict):
    for q in knowladge_base["questions"]:
        if q["question"] == question:
            return q["answer"]
    return None

def chat_bot():
    file_path=dirname + "/SimpleIA_knowladge.json"
    know = load_knowledge(file_path)
    while True:
        user_input : str = input("Enter your question: ")
        if user_input.lower() == "exit":
            print("Bot: Bye Bye!")
            break
        best_match = find_best_match(user_input,[ q["question"] for q in know["questions"]])

        if best_match:
            answer = get_answer_for_question(best_match,know)
            print(f'Bot: {answer}')
        else:
            print("Bot: I don't understand")
            new_answer = input("Enter your answer or 'skip': ")
            if new_answer.lower() != "skip":
                know["questions"].append({"question":user_input,"answer":new_answer})
                save_knowledge(file_path,know)
                print("Bot: Thanks! I learned it!")
            else:
                print("Bot: I don't understand")



   
if __name__ == "__main__":
    print_hi('PyCharm')
    chat_bot()

