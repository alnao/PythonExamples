# AWS CDK 25 - VPC con endpoint e Client VPN

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Una **VPC** completa su due zone di disponibilità, con gli **endpoint gateway** di S3 e DynamoDB e, se configurato, un **AWS Client VPN endpoint** per entrare nella rete privata dal proprio PC. Versione CDK in Python dell'esempio CloudFormation [Esempio25vpcEndpoint](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio25vpcEndpoint), che usava il template ufficiale *ecs-refarch-cloudformation* per la VPC e un template annidato per il Client VPN con autenticazione SAML.

- **🌐 VPC** `10.184.0.0/16`: subnet pubbliche `10.184.0.0/24` e `10.184.1.0/24` (con Internet gateway), subnet private isolate `10.184.2.0/24` e `10.184.3.0/24`, **nessun NAT gateway** (le subnet private non escono su Internet)
- **🚪 Endpoint gateway** per **S3** e **DynamoDB**: il traffico verso i due servizi resta nella rete AWS anche dalle subnet private, ed è gratuito
- **📜 Flow log** del traffico rifiutato in CloudWatch Logs (7 giorni), per capire cosa bloccano security group e NACL
- **🔐 Client VPN facoltativo**: si crea solo passando il certificato server ACM e un'autenticazione, con **certificato client** (*mutual authentication*) oppure **SAML** (come l'esempio CloudFormation); *split tunnel*, DNS della VPC, log delle connessioni, associato alle due subnet private
- **🛡️ Security group di default senza regole** (feature flag `restrictDefaultSecurityGroup` di `cdk.json`, applicata da una piccola Lambda di CDK al deploy)

Il Client VPN costa circa **0,10 $/ora per ogni subnet associata** anche senza nessuno collegato (~146 $/mese con due subnet): per questo senza parametri lo stack crea solo la rete, che non costa nulla.

| Context (`-c`) | Valore | Effetto |
|----------------|--------|---------|
| `server_certificate_arn` | ARN del certificato server in ACM | crea il Client VPN |
| `client_certificate_arn` | ARN del certificato della CA dei client in ACM | autenticazione con certificato client |
| `saml_provider_arn` | ARN dell'identity provider SAML in IAM | autenticazione federata (es. IAM Identity Center, Okta, Entra ID) |
| `self_service_saml_provider_arn` | ARN del provider SAML del portale self-service | attiva il portale da cui scaricare la configurazione |


## 🔧 Architettura

```
VPC 10.184.0.0/16 (2 zone)
├── subnet pubbliche 10.184.0.0/24, 10.184.1.0/24 ── Internet gateway
├── subnet private   10.184.2.0/24, 10.184.3.0/24 ── nessuna uscita su Internet
├── endpoint gateway S3 e DynamoDB (rotte in tutte le tabelle di routing)
└── flow log (REJECT) ── CloudWatch Logs /vpc/<stack>/flow-logs

PC ── OpenVPN (TCP 443) ── Client VPN endpoint, client 10.185.0.0/22 ──┬── associazione subnet privata 1
                                                                        └── associazione subnet privata 2
      split tunnel: solo 10.184.0.0/16 passa nella VPN; DNS 10.184.0.2; log /vpn/<stack>/connections
```

```
├── app.py                          # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk25vpc_endpoint/
│   ├── cdk25vpc_endpoint_stack.py  # 🏗️ VPC, endpoint gateway, flow log, Client VPN facoltativo
│   └── tags.py                     # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── tests/unit/                     # 🧪 test dello stack (sintesi locale, senza AWS)
└── cdk.json, requirements*.txt
```


## 🛠️ Deploy

```bash
cd PythonExamples/AWS/CDK/cdk25vpcEndpoint/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit

#../bootstrap/bootstrap.sh create eu-central-1
cdk deploy      # solo VPC, endpoint e flow log
```
Al termine `cdk deploy` stampa `VpcId`, `PublicSubnets` e `PrivateSubnets`: la VPC si può usare per gli altri esempi che chiedono una VPC esistente (le subnet private però non hanno NAT, quindi non vanno bene per il cdk21 che scarica pacchetti da Internet).

**Client VPN con certificati** (dalla [guida AWS](https://docs.aws.amazon.com/vpn/latest/clientvpn-admin/client-auth-mutual-enable.html), con easy-rsa):
```bash
git clone https://github.com/OpenVPN/easy-rsa.git && cd easy-rsa/easyrsa3
./easyrsa init-pki
./easyrsa build-ca nopass
./easyrsa --san=DNS:server build-server-full server nopass
./easyrsa build-client-full client1.domain.tld nopass
REGION=eu-central-1
TAGS="Key=Name,Value=aws-py-CDK.cdk25vpcEndpoint Key=Environment,Value=dev Key=Project,Value=Development.aws.py-CDK.cdk25vpcEndpoint Key=Owner,Value=AlNao Key=CostCenter,Value=dev Key=ManagedBy,Value=Sh"
SERVER=$(aws acm import-certificate --certificate fileb://pki/issued/server.crt --private-key fileb://pki/private/server.key --certificate-chain fileb://pki/ca.crt --tags $TAGS --region $REGION --query CertificateArn --output text)
CLIENT=$(aws acm import-certificate --certificate fileb://pki/issued/client1.domain.tld.crt --private-key fileb://pki/private/client1.domain.tld.key --certificate-chain fileb://pki/ca.crt --tags $TAGS --region $REGION --query CertificateArn --output text)
cd -
cdk deploy -c server_certificate_arn=$SERVER -c client_certificate_arn=$CLIENT
```
Il deploy del Client VPN dura 5-10 minuti (associazione delle subnet). Poi l'output `ClientVpnConfigCommand` scarica il file `cdk25-client.ovpn`: va completato con il certificato e la chiave del client e importato nel client AWS VPN o OpenVPN.
```bash
aws ec2 export-client-vpn-client-configuration --client-vpn-endpoint-id cvpn-endpoint-xxx --region $REGION --output text > cdk25-client.ovpn
echo "<cert>$(cat easy-rsa/easyrsa3/pki/issued/client1.domain.tld.crt)</cert>" >> cdk25-client.ovpn
echo "<key>$(cat easy-rsa/easyrsa3/pki/private/client1.domain.tld.key)</key>" >> cdk25-client.ovpn
```

**Client VPN con SAML** (come l'esempio CloudFormation): serve un identity provider SAML già configurato in IAM; `cdk deploy -c server_certificate_arn=$SERVER -c saml_provider_arn=arn:aws:iam::<account>:saml-provider/<nome>`.

Comandi utili:
```bash
aws ec2 describe-vpcs --filters Name=tag:Project,Values=Development.aws.py-CDK.cdk25vpcEndpoint --query "Vpcs[].[VpcId,CidrBlock]" --output table
aws ec2 describe-vpc-endpoints --filters Name=vpc-id,Values=vpc-xxx --query "VpcEndpoints[].[ServiceName,VpcEndpointType,State]" --output table
aws ec2 describe-client-vpn-endpoints --query "ClientVpnEndpoints[].[ClientVpnEndpointId,Status.Code,DnsName]" --output table
aws ec2 describe-client-vpn-connections --client-vpn-endpoint-id cvpn-endpoint-xxx
aws logs tail /vpc/Cdk25VpcEndpointStack/flow-logs --since 10m
```

**Tag**: tutte le risorse hanno i tag standard del repository (`Project=Development.aws.py-CDK.cdk25vpcEndpoint`, `ManagedBy=CDK`); il Client VPN endpoint li riceve in `TagSpecifications`, perché CloudFormation non accetta `Tags` su quella risorsa. Non hanno tag solo i tipi che CloudFormation non permette di taggare: rotte, associazioni delle subnet, attacco dell'Internet gateway, endpoint gateway, associazioni e regole del Client VPN, policy IAM inline. I certificati importati con il comando sopra hanno i tag con `ManagedBy=Sh`.


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS.

| Voce | Calcolo | Al mese (30 gg) |
|------|---------|-----------------|
| VPC, subnet, Internet gateway, tabelle di routing | gratuiti | 0 $ |
| Endpoint gateway S3 e DynamoDB | gratuiti (gli endpoint *interface* costerebbero ~0,012 $/ora per zona) | 0 $ |
| Flow log | solo traffico rifiutato, pochi MB × 0,63 $/GB + storage | < 0,10 $ |
| **Totale senza Client VPN** | | **~0 $** |
| Client VPN, associazioni | 2 subnet × 0,10 $/ora | ~146 $ |
| Client VPN, connessioni | 0,05 $/ora per ogni client collegato | 0,05 $/ora |
| ACM | certificati importati gratuiti | 0 $ |
| **Totale con Client VPN** | | **~146 $ + connessioni** |

Il Client VPN si paga da quando è associato, non da quando qualcuno si collega: per una prova conviene creare, provare e distruggere lo stesso giorno (oppure associare una sola subnet).


## 🧹 Pulizia

```bash
cdk destroy
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk25vpcEndpoint --query "ResourceTagMappingList[].ResourceARN" --output text
# certificati importati per il Client VPN (non sono creati dallo stack)
aws acm delete-certificate --certificate-arn $SERVER --region $REGION
aws acm delete-certificate --certificate-arn $CLIENT --region $REGION
```
- per togliere solo il Client VPN e tenere la rete basta rifare `cdk deploy` senza i `-c` del Client VPN
- gli identity provider SAML non sono creati dallo stack: se creati solo per questo esempio, `aws iam delete-saml-provider --saml-provider-arn <arn>`
- il bootstrap resta (condiviso con gli altri progetti CDK): `../bootstrap/bootstrap.sh destroy <region>` quando nella region non ci sono più stack CDK


## 🚀 Sviluppi Futuri
- 🔌 **Endpoint interface** (Secrets Manager, ECR, CloudWatch Logs) per usare le subnet isolate con ECS o Lambda senza NAT
- 🔀 **Transit Gateway** o **VPC peering** con una seconda VPC
- 🧭 **Site-to-Site VPN** verso una rete aziendale e **Route 53 Resolver** per il DNS ibrido


# &lt; AlNao /&gt;
Tutti i codici sorgente e le informazioni presenti in questo repository sono frutto di un attento e paziente lavoro di sviluppo da parte di AlNao, che si è impegnato a verificarne la correttezza nella massima misura possibile. Qualora parte del codice o dei contenuti sia stato tratto da fonti esterne, la relativa provenienza viene sempre citata, nel rispetto della trasparenza e della proprietà intellettuale. 


Alcuni contenuti e porzioni di codice presenti in questo repository sono stati realizzati anche grazie al supporto di strumenti di intelligenza artificiale, il cui contributo ha permesso di arricchire e velocizzare la produzione del materiale. Ogni informazione e frammento di codice è stato comunque attentamente verificato e validato, con l’obiettivo di garantire la massima qualità e affidabilità dei contenuti offerti. 


Per ulteriori dettagli, approfondimenti o richieste di chiarimento, si invita a consultare il sito [AlNao.it](https://www.alnao.it/).


## License
Made with ❤️ by <a href="https://www.alnao.it">AlNao</a>
&bull; 
Public projects 
<a href="https://www.gnu.org/licenses/gpl-3.0"  valign="middle"> <img src="https://img.shields.io/badge/License-GPL%20v3-blue?style=plastic" alt="GPL v3" valign="middle" /></a>
*Free Software!*


Il software è distribuito secondo i termini della GNU General Public License v3.0. L'uso, la modifica e la ridistribuzione sono consentiti, a condizione che ogni copia o lavoro derivato sia rilasciato con la stessa licenza. Il contenuto è fornito "così com'è", senza alcuna garanzia, esplicita o implicita.


The software is distributed under the terms of the GNU General Public License v3.0. Use, modification, and redistribution are permitted, provided that any copy or derivative work is released under the same license. The content is provided "as is", without any warranty, express or implied.

