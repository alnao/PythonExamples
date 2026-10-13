"""
Adatta il template ufficiale di "cdk bootstrap" ai nomi del repository:
- default del qualifier e dei nomi del bucket degli asset e del repository ECR
- nome del parametro SSM con la versione del bootstrap: il template lo costruisce come
  /cdk-bootstrap/<qualifier>/version e il qualifier non ammette "/", quindi va sostituito

Usa solo la libreria standard e modifica il testo (i commenti del template restano);
se il template cambia formato lo script si ferma invece di produrre un template sbagliato.

Uso: python3 patch_template.py ORIGINALE MODIFICATO NOME QUALIFIER PARAMETRO_SSM
"""

import re
import sys


def set_default(text: str, parameter: str, value: str) -> str:
    """Cambia il Default di un parametro del template (blocco indentato di 4 spazi)."""
    pattern = re.compile(rf"(\n  {parameter}:\n(?:    .*\n)*?    Default: )[^\n]*")
    text, count = pattern.subn(lambda m: m.group(1) + f"'{value}'", text, count=1)
    if count != 1:
        sys.exit(f"Parametro {parameter} non trovato nel template")
    return text


VERSION_PATH = r"/cdk-bootstrap/\$\{Qualifier\}/version"
VERSION_NAME_PATTERNS = [
    # YAML: "Name:" seguito da Fn::Sub o !Sub, sulla stessa riga o sotto, con o senza virgolette
    # o tra graffe, es.  Name:\n  Fn::Sub: '/cdk-bootstrap/${Qualifier}/version'
    #                    Name: !Sub /cdk-bootstrap/${Qualifier}/version
    #                    Name: {Fn::Sub: "/cdk-bootstrap/${Qualifier}/version"}
    (re.compile(r"Name:[ \t]*(?:\n[ \t]+)?(?:\{[ \t]*)?(?:Fn::Sub:|!Sub)[ \t]*(['\"]?)"
                + VERSION_PATH + r"\1(?:[ \t]*\})?"), "Name: '{name}'"),
    # JSON: "Name": {"Fn::Sub": "/cdk-bootstrap/${Qualifier}/version"}
    (re.compile(r'"Name":\s*\{\s*"Fn::Sub":\s*"' + VERSION_PATH + r'"\s*\}'), '"Name": "{name}"'),
]


def set_version_parameter(text: str, name: str) -> str:
    """Nome fisso per il parametro SSM CdkBootstrapVersion."""
    for pattern, replacement in VERSION_NAME_PATTERNS:
        new_text, count = pattern.subn(replacement.replace("{name}", name), text)
        if count == 1:
            return new_text
    # formato non previsto: si mostrano le righe del template da cui ricavarlo
    lines = text.splitlines()
    context = [f"{j + 1:5}: {lines[j]}" for i, line in enumerate(lines) if "cdk-bootstrap/" in line
               for j in range(max(0, i - 2), min(len(lines), i + 2))]
    sys.exit("Nome del parametro SSM /cdk-bootstrap/${Qualifier}/version non trovato nel template.\n"
             "Righe del template che lo contengono:\n" + ("\n".join(context) or "(nessuna)"))


def main():
    if len(sys.argv) != 6:
        sys.exit(__doc__)
    source, target, name, qualifier, version_parameter = sys.argv[1:]
    text = open(source).read()
    text = set_default(text, "Qualifier", qualifier)
    text = set_default(text, "FileAssetsBucketName", name)
    text = set_default(text, "ContainerAssetsRepositoryName", name)
    text = set_version_parameter(text, version_parameter)
    open(target, "w").write(text)
    print(f"Template adattato: {target}")


if __name__ == "__main__":
    main()
