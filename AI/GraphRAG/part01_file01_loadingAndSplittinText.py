"""
    python3 -m venv .venv  
    source .venv/bin/activate  
    pip install graphrag
    python3 -m pip install langchain-text-splitters
    python3 part01_file01_loadingAndSplittinText.py

  
  graphrag init --root /mnt/Dati/daSmistare/test/input/
  python -m graphrag index --root /mnt/Dati/daSmistare/test/
  
  
  
  run --name "Loading and Splitting Text" --command "python3 file.py" --watch

  python3 file.py  
    #  deactivate # exit

"""
from langchain_text_splitters import TokenTextSplitter

with open("/mnt/Dati/daSmistare/test/input/sig.txt", 'r', encoding='utf-8', errors='replace') as file:
    content = file.read()

text_splitter = TokenTextSplitter(chunk_size=1200, chunk_overlap=100)

texts = text_splitter.split_text(content)

print ("Chunks" , len (texts))