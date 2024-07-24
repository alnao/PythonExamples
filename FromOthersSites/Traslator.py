#see https://huggingface.co/spaces/Mediocreatmybest/PipelineTranslator/blob/main/app.py

import torch
import gradio as gr
from transformers import pipeline
import ast

translation_task_names = {
    'English to French': 'translation_en_to_fr',
#    'French to English': 'translation_fr_to_en',
#    'English to Spanish': 'translation_en_to_es',
#    'Spanish to English': 'translation_es_to_en',
    'English to German': 'translation_en_to_de',
#    'German to English': 'translation_de_to_en',
#    'English to Italian': 'translation_en_to_it',
#    'Italian to English': 'translation_it_to_en',
    'English to Dutch': 'translation_en_to_nl',
    'Dutch to English': 'translation_nl_to_en',
#    'English to Portuguese': 'translation_en_to_pt',
#    'Portuguese to English': 'translation_pt_to_en',
    'English to Russian': 'translation_en_to_ru',
    'Russian to English': 'translation_ru_to_en',
    'English to Chinese': 'translation_en_to_zh',
    'Chinese to English': 'translation_zh_to_en',
#    'English to Japanese': 'translation_en_to_ja',
#    'Japanese to English': 'translation_ja_to_en',
    'English to Romanian': 'translation_en_to_ro',
    'Swedish to English': 'translation_SV_to_EN',
}

model_names = {
    'T5-Base': 't5-base',
    'T5-Small': 't5-small',
    'T5-Large': 't5-large',
    'Opus-En-ZH': 'liam168/trans-opus-mt-en-zh',
    'Opus-ZH-En': 'Helsinki-NLP/opus-mt-zh-en',
    'DDDSSS/translation_en-zh': 'DDDSSS/translation_en-zh',
    'T5-Base-nl-en': 'yhavinga/t5-base-36L-ccmatrix-multi',
    'T5-Small-nl-en': 'yhavinga/t5-small-24L-ccmatrix-multi',
    'Opus-Sv-En': 'Helsinki-NLP/opus-mt-sv-en',
    'Opus-En-Ru': 'Helsinki-NLP/opus-mt-en-ru',
    'Opus-Ru-En': 'Helsinki-NLP/opus-mt-ru-en',
}

# Create a dictionary to store loaded models
loaded_models = {}

# Simple translation function
def translate_text(model_choice, task_choice, text_input, load_in_8bit, device):
    model_key = (model_choice, task_choice, load_in_8bit)  # Create a tuple to represent the unique combination of task and 8bit loading

    # Check if the model is already loaded
    if model_key in loaded_models:
        translator = loaded_models[model_key]
    else:
        model_kwargs = {"load_in_8bit": load_in_8bit} if load_in_8bit else {}
        dtype = torch.float16 if load_in_8bit else torch.float32  # Set dtype based on the value of load_in_8bit
        translator = pipeline(task=translation_task_names[task_choice],
                            model=model_names[model_choice],  # Use selected model
                            device=device,  # Use selected device
                            model_kwargs=model_kwargs, 
                            torch_dtype=dtype,  # Set the floating point
                            use_fast=True
                            )
        # Store the loaded model
        loaded_models[model_key] = translator

    translation = translator(text_input)[0]['translation_text']
    return str(translation).strip()

def launch(model_choice, task_choice, text_input, load_in_8bit, device):
    return translate_text(model_choice, task_choice, text_input, load_in_8bit, device)

model_dropdown = gr.Dropdown(choices=list(model_names.keys()), label='Select Model')
task_dropdown = gr.Dropdown(choices=list(translation_task_names.keys()), label='Select Translation Task')
text_input = gr.Textbox(label="Input Text")  # Single line text input
load_in_8bit = gr.Checkbox(label="Load model in 8bit")
# https://www.gradio.app/docs/radio
device = gr.Radio(['cpu', 'cuda'], label='Select device', value='cpu')

iface = gr.Interface(launch, inputs=[model_dropdown, task_dropdown, text_input, load_in_8bit, device], 
                     outputs=gr.Textbox(type="text", label="Translation"))
iface.launch()