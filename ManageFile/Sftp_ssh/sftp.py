#https://stackoverflow.com/questions/3635131/paramikos-sshclient-with-sftp
#pip install paramiko
import paramiko
from io import StringIO #from StringIO import StringIO

def sftp_simple_connect(host,port,username,password):
    transport = paramiko.Transport((host,port))
    transport.connect(None,username,password)
    sftp = paramiko.SFTPClient.from_transport(transport)
    return sftp

def sftp_get_file(connection, remotepath, localpath ):
    connection.get(remotepath,localpath)

def sftp_put_file(connection, remotepath, localpath ):
    connection.put(localpath,remotepath)

def sftp_key_connect(host,port,username,pkey):
    fkey = open(pkey)
    skey = fkey.read()
    key = paramiko.RSAKey.from_private_key(StringIO(skey))
    transport = paramiko.Transport((host, port))
    transport.connect(
        username=username,
        password='',
        pkey=key
    )
    sftp = paramiko.SFTPClient.from_transport(transport)
    return sftp

def openSSHconnection(host,username,pkey):
    ssh = paramiko.SSHClient()
    private_key = paramiko.RSAKey.from_private_key_file(pkey)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=username, password='', pkey=private_key)
    return ssh

if __name__ == '__main__':
    print("__main__ del sftp.py")
    paramiko.util.log_to_file("C:\\Temp\\paramiko.log")

    host = '34.251.28.90'
    port = 22
    username = 'utente'
    password = ''
    localpath = 'C:\\Temp\\a.txt'
    remotepath = 'prova.txt' #\\home\\bitnami\\
    pkey="AlbertoNao_privata.pem"
    command="ls -la"
    
#SFTP connect, put file and get file
    #connection=sftp_simple_connect(host,port,username,password)+
    connection_sftp = sftp_key_connect(host,port,username,pkey)
    sftp_put_file(connection_sftp, remotepath, localpath )
    sftp_get_file(connection_sftp, remotepath, localpath )
    if connection_sftp: 
        connection_sftp.close()
    #if transport: transport.close()
    print("SFTP finito")

#SSH connect and command
    connection_ssh = openSSHconnection(host,username,pkey)
    ssh_stdin, ssh_stdout, ssh_stderr = connection_ssh.exec_command(command)
    stdout=ssh_stdout.readlines()
    print("SSH finito" , stdout )
