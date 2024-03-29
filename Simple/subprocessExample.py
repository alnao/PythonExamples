import subprocess
import shlex
import os

def executeCommand(command):
    print("Run "+command)
    args = shlex.split(command)
    try:
        proc = subprocess.Popen(args,shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out, err = proc.communicate()
        rc = proc.returncode
        if rc != 0:
            print("Comando andato in errore: "+command)
        print(out)
    except OSError as e:
        print(e)
        return None
    return rc
comando="dir "
executeCommand(comando)

class NmapPy():
    def __init__(self, command=[]):
        self.command=command
    def scan(self):
        try:
            p=subprocess.Popen(self.command, shell=False,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out,err=p.communicate()
            print("\n Nmap scan is complete : ")
            print(str(out))
            print(str(err))
        except Exception as ex:
            print("Exception caught : "+str(ex))
nmap=NmapPy(["nmap", "-Pn", "-sV", "127.0.0.1"])
nmap.scan()