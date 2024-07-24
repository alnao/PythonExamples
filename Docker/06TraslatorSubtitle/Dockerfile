FROM jupyter/tensorflow-notebook

USER root
# $NB_UID 
#jovyan in image or root

RUN pip install --upgrade pip && \ 
    pip install transformers && \
    pip install pysrt && \
    fix-permissions "/home/${NB_USER}"

COPY captions_english.srt ./
COPY Translator.ipynb ./


