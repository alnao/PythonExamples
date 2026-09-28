"""SSM Parameter Store: elenco dei parametri (valori decifrati) e modifica del valore."""

from aws.services import paginate


class AwsSsmParameters:
    def __init__(self, session):
        self.client = session.client('ssm')

    def parameters(self, path='/'):
        return paginate(self.client, 'get_parameters_by_path', 'Parameters',
                        Path=path, Recursive=True, WithDecryption=True)

    def put_value(self, name, value):
        """Nuovo valore di un parametro esistente, mantenendo il suo tipo."""
        current = self.client.get_parameter(Name=name)['Parameter']
        self.client.put_parameter(Name=name, Value=value, Type=current['Type'], Overwrite=True)
        return self.client.get_parameter(Name=name, WithDecryption=True)['Parameter']
