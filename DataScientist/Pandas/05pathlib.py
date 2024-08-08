#see https://khuyentran1401.github.io/Efficient_Python_tricks_and_tools_for_data_scientists/Chapter2/pathlib.html
import os
from pathlib import Path
path = '/home/alnao/'
file = 'new_file.txt'
# Create a new directory if not exist
if not os.path.exists(path):
    os.makedirs(path)
# Create new file inside new directory
with open(os.path.join(path, file), 'wb'):
    pass

#with from pathlib import Path
# Create a new directory
folder = Path(path)
folder.mkdir(exist_ok=True)
# Create new file inside new directory
file = folder / file
file.touch()


#path home
path = Path.home()
docs = path / 'Documents'
pictures = path / 'Pictures'
print(docs)
print(pictures)

#Get the Parent of the Current Path with pathlib
path = Path.cwd()
print(f'Current path: {path}')
print(f'Parent of the current path: {path.parent}')
print(f'Grandparent of the current path: {path.parent.parent}')


#Get the Path Relative to Another Path
from pathlib import Path
nlp = Path('/mnt/Dati/backup/')
root = '/mnt/'
print  ( nlp.relative_to(root) )


#Check if Two File Paths Are the Same
home = Path.home()
absolute = home / "/home/alnao/new_file.txt"
relative = Path("05pathlib.py")
print (absolute.samefile(relative))