"""Lambda facoltativa: un file caricato in TOSENDSFTP/ viene inviato a un server SFTP (paramiko, dal layer).

La chiave privata (RSA o Ed25519, formato PEM/OpenSSH) e' un parametro SSM SecureString creato a mano:
lo stack ne conosce solo il nome (variabile SFTP_KEY_PARAM).
"""

import io
import os

from common import client, s3_object


def load_key(text: str):
    import paramiko  # nel layer delle librerie (build_layer.sh)

    for key_class in (paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey):
        try:
            return key_class.from_private_key(io.StringIO(text))
        except paramiko.SSHException:
            continue
    raise ValueError("chiave privata SFTP non riconosciuta (RSA, Ed25519 o ECDSA)")


def send(event, context):
    import paramiko

    bucket, key = s3_object(event)
    private_key = load_key(client("ssm").get_parameter(Name=os.environ["SFTP_KEY_PARAM"],
                                                       WithDecryption=True)["Parameter"]["Value"])
    remote_path = os.path.basename(key)
    transport = paramiko.Transport((os.environ["SFTP_HOST"], int(os.environ.get("SFTP_PORT", "22"))))
    try:
        transport.connect(username=os.environ["SFTP_USER"], pkey=private_key)
        sftp = paramiko.SFTPClient.from_transport(transport)
        with sftp.open(remote_path, "wb", 32768) as remote_file:
            client("s3").download_fileobj(bucket, key, remote_file)
        print(f"inviato s3://{bucket}/{key} -> sftp://{os.environ['SFTP_HOST']}/{remote_path}")
    finally:
        transport.close()
    return {"file": key, "remoto": remote_path}
