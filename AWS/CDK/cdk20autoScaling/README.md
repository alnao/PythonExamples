# CDK20 AutoScaling
Esempio base per la creazione di un autoscaling group con un ALB, le istanze avviano Apache autonomo senza disco EFS condiviso

Per l'installazione e la configurazione della CLI e del tool CDK, vedere il file README globale.

## Comandi 
- Creazione del progetto
    ```
    cdk init app --language python
    python3 -m pip install -r requirements.txt
    python3 -m venv .venv
    cdk bootstrap
    ```

- Deploy del progetto
    ```
    cdk ls
    cdk synth > Cdk20AG-template.yaml
    cdk deploy --parameters vpcid=vpc-0013c2751d04a7413 --parameters keyname=AlbertoNaoFormazione --parameters publicsubnetids1=subnet-0b6f53c0291c13f02 --parameters publicsubnetids2=subnet-08d2c516da5786c77 --parameters privatesubnetid1=subnet-0ca3ce54f35c3d3ef --parameters privatesubnetid2=subnet-08dbf4b5fed6a83b2
    ```
- Comando verifica dello stack
    ```
    aws cloudformation list-stack-resources --stack-name Cdk20AG --output text
    aws cloudformation list-stack-resources --stack-name Cdk20AG --output table
    aws cloudformation get-template --stack-name Cdk20AG
    ```

- Confronto tra sviluppo e ambiente target
    ```
    cdk diff 
    ```
- Distruzione dello stack con rimozione di tutte le risorse
    ```    
    cdk destroy
    ```


# AlNao.it
Nessun contenuto in questo repository è stato creato con IA o automaticamente, tutto il codice è stato scritto con molta pazienza da Alberto Nao. Se il codice è stato preso da altri siti/progetti è sempre indicata la fonte. Per maggior informazioni visitare il sito [alnao.it](https://www.alnao.it/).

## License
Public projects 
<a href="https://it.wikipedia.org/wiki/GNU_General_Public_License"  valign="middle"><img src="https://img.shields.io/badge/License-GNU-blue" style="height:22px;"  valign="middle"></a> 
*Free Software!*









# Welcome to your CDK Python project!

This is a blank project for CDK development with Python.

The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!
