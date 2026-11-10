# AWS CDK 27 - Cluster EKS

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati: il solo control plane di EKS costa circa 73 $ al mese ⚠️

## 🚀 Panoramica

Un cluster **Amazon EKS** (Kubernetes gestito) con un **node group** di istanze EC2 e un database **RDS MySQL**, nella VPC di default, su cui gira il microservizio Java Spring Boot dell'esempio [JavaSpringBootExample](https://github.com/alnao/JavaSpringBootExample) (immagine `alnao/j-esempio02-backend-springboot` su Docker Hub). Versione CDK in Python dell'esempio CloudFormation [Esempio27eks](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio27eks).

- **☸️ Cluster EKS** con API pubblica e privata, log del control plane (`api`, `audit`) in CloudWatch con 7 giorni, **supporto standard** (una versione in supporto esteso costerebbe 0,60 $/ora invece di 0,10)
- **🔑 Access entry**: l'utente o ruolo IAM passato come parametro è amministratore del cluster (con CDK chi crea il cluster è il ruolo di CloudFormation del bootstrap, che non è chi usa `kubectl`)
- **🖥️ Node group gestito** Amazon Linux 2023 (`t3.small`, da 1 a 2 nodi), con un launch template per disco gp3 cifrato, IMDSv2 e i tag su istanze e volumi
- **📏 Add-on metrics-server** per l'`HorizontalPodAutoscaler` del manifest
- **🗄️ RDS MySQL 8.4** raggiungibile solo dal security group del cluster, password **generata e custodita da RDS** in Secrets Manager (nessuna password nel template o nei parametri)
- **📄 Manifest** `k8s/springboot-k8s.yaml`: Deployment, Service `LoadBalancer` (Network Load Balancer con i tag dell'esempio) e HPA; endpoint e password del database da un Secret di Kubernetes

Come il template CloudFormation lo stack usa le risorse **L1** (`CfnCluster`, `CfnNodegroup`, `CfnAccessEntry`, `CfnAddon`): il costrutto L2 `eks.Cluster` aggiungerebbe una Lambda con `kubectl`, un layer e diversi custom resource, utili per installare i manifest da CDK ma non necessari qui.

Differenze rispetto al template CloudFormation:
| | CloudFormation (Esempio27) | CDK (cdk27) |
|---|---|---|
| Accesso a `kubectl` | il creatore del cluster (utente che lancia `sam deploy`) | access entry per il principal passato come parametro |
| Password MySQL | parametro con default nel template | gestita da RDS (`ManageMasterUserPassword`), letta da Secrets Manager |
| Accesso al database | security group aggiuntivo del control plane e tutta la VPC `172.31.0.0/16` | solo il security group del cluster (usato anche dai nodi) |
| HPA | senza metrics-server (non poteva funzionare) | add-on metrics-server |
| Supporto | non specificato | `UpgradePolicy` STANDARD |
| Database al destroy | snapshot finale | nessuno snapshot |


## 🔧 Architettura

```
kubectl (PC) ── access entry (AmazonEKSClusterAdminPolicy) ── EKS control plane (log api/audit → /aws/eks/<cluster>/cluster)
                                                                    │
VPC di default ── node group (1-2 × t3.small, AL2023) ── pod springboot-app (2 repliche, HPA 1-2)
                     │                                       ├── Secret mysql (host, password)
                     │                                       └── RDS MySQL :3306 (solo dal security group del cluster)
Internet ── Network Load Balancer (creato da Kubernetes, tag ManagedBy=Sh) ── Service springboot-app-service :80 → 8080
```

```
├── app.py                 # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk27eks/
│   ├── cdk27eks_stack.py  # 🏗️ ruoli, cluster, access entry, launch template, node group, add-on, RDS
│   └── tags.py            # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── k8s/springboot-k8s.yaml  # ☸️ Deployment, Service LoadBalancer, HorizontalPodAutoscaler
├── tests/unit/            # 🧪 test dello stack (sintesi locale, senza AWS)
└── cdk.json, requirements*.txt
```


## 🛠️ Deploy

Prerequisiti: Python 3.12+, Node.js e AWS CDK v2 (`npm install -g aws-cdk`), credenziali AWS configurate, `kubectl`. Controllare le [versioni di Kubernetes](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html) in supporto standard e, se serve, passare `kubernetesversion`.

```bash
cd PythonExamples/AWS/CDK/cdk27eks/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit

# VPC di default (o l'unica presente) e sue subnet recuperate con la CLI (sola lettura) e salvate come variabili d'ambiente
export REGION=eu-central-1 AWS_REGION=eu-central-1   # AWS_REGION: la usa anche cdk deploy per scegliere la region
export DEFAULT_VPC=$(aws ec2 describe-vpcs --region $REGION --filters Name=isDefault,Values=true --query "Vpcs[0].VpcId" --output text)
if [ "$DEFAULT_VPC" = "None" ]; then   # nessuna VPC di default: l'unica presente nella region
  VPCS=($(aws ec2 describe-vpcs --region $REGION --query "Vpcs[].VpcId" --output text))
  if [ ${#VPCS[@]} -eq 1 ]; then export DEFAULT_VPC=${VPCS[0]}; else echo "nessuna VPC di default e ${#VPCS[@]} VPC nella region: impostare DEFAULT_VPC a mano"; fi
fi
export SUBNETS=$(aws ec2 describe-subnets --region $REGION --filters Name=vpc-id,Values=$DEFAULT_VPC --query "sort_by(Subnets,&AvailabilityZone)[0:3].SubnetId" --output text | tr '\t' ',')
echo "VPC $DEFAULT_VPC - subnet $SUBNETS"
# amministratore del cluster: un utente IAM (arn:aws:iam::<account>:user/<nome>) o il ruolo IAM della propria sessione
#   (con SSO l'ARN di get-caller-identity e' assumed-role/...: serve quello del ruolo, arn:aws:iam::<account>:role/aws-reserved/sso.amazonaws.com/...)
export ADMIN=$(aws sts get-caller-identity --query Arn --output text)

#../bootstrap/bootstrap.sh create $REGION
cdk deploy --parameters vpcid=$DEFAULT_VPC --parameters subnetids=$SUBNETS --parameters adminprincipalarn=$ADMIN
```
Parametri facoltativi: `clustername` (default `cdk27eks-cluster`), `kubernetesversion` (default `1.35`), `nodeinstancetype` (default `t3.small`). Il deploy dura circa 20 minuti (cluster 10, node group 5, database 10 in parallelo).

Al termine `cdk deploy` stampa `ClusterName`, `ClusterEndpoint`, `KubectlCommand`, `MySQLEndpoint` e `MySQLSecretArn`. Installazione del microservizio:
```bash
STACK=Cdk27EksStack
out() { aws cloudformation describe-stacks --stack-name $STACK --region $REGION --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
aws eks update-kubeconfig --region $REGION --name $(out ClusterName)
kubectl get nodes

RDS_HOST=$(out MySQLEndpoint)
RDS_PASSWORD=$(aws secretsmanager get-secret-value --region $REGION --secret-id $(out MySQLSecretArn) --query SecretString --output text | python3 -c 'import json,sys; print(json.load(sys.stdin)["password"])')
kubectl create secret generic mysql --from-literal=host=$RDS_HOST --from-literal=password=$RDS_PASSWORD
kubectl apply -f k8s/springboot-k8s.yaml

kubectl get pods,svc,hpa
LB=$(kubectl get service springboot-app-service -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
curl http://$LB/api/persone/info      # il Network Load Balancer impiega 2-3 minuti a diventare attivo
```
RDS ruota la password ogni 7 giorni: dopo una rotazione il Secret di Kubernetes va ricreato (`kubectl delete secret mysql`, poi i due comandi sopra e `kubectl rollout restart deployment springboot-app`).

Comandi utili:
```bash
aws eks describe-cluster --name cdk27eks-cluster --query "cluster.[status,version,platformVersion]"
aws eks list-nodegroups --cluster-name cdk27eks-cluster
aws eks list-access-entries --cluster-name cdk27eks-cluster
aws eks describe-addon --cluster-name cdk27eks-cluster --addon-name metrics-server --query "addon.[status,addonVersion]"
kubectl top pods
kubectl logs deployment/springboot-app --tail 50
```

**Tag**: tutte le risorse dello stack hanno i tag standard del repository (`Project=Development.aws.py-CDK.cdk27eks`, `ManagedBy=CDK`), anche istanze e volumi dei nodi (dal launch template). Il Network Load Balancer è creato da Kubernetes, non da CloudFormation: riceve gli stessi tag con `ManagedBy=Sh` dall'annotazione `aws-load-balancer-additional-resource-tags` del manifest. Il segreto creato da RDS per la password non è una risorsa dello stack.


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS e di [Amazon EKS](https://aws.amazon.com/eks/pricing/). Lo stack ha costi fissi orari anche senza traffico.

| Voce | Calcolo | Al mese (30 gg) |
|------|---------|-----------------|
| Control plane EKS (supporto standard) | 0,10 $/ora | 73 $ |
| Nodi `t3.small` | 1-2 × 0,024 $/ora | 17-35 $ |
| EBS dei nodi | 20 GB gp3 × 0,095 $/GB per nodo | 2-4 $ |
| IP pubblici dei nodi (VPC di default) | 1-2 × 0,005 $/ora | 4-7 $ |
| RDS `db.t4g.micro` | 0,017 $/ora + 20 GB gp3 | ~15 $ |
| Secrets Manager (segreto di RDS) | 0,40 $ | 0,40 $ |
| Network Load Balancer (creato da Kubernetes) | 0,027 $/ora + NLCU + IP pubblici | ~25 $ |
| CloudWatch Logs (api e audit) | qualche centinaio di MB al mese, 7 giorni | 0,50-2 $ |
| **Totale** | | **~140-160 $** |

Per una prova di qualche ora il costo è di pochi dollari: conviene creare, provare e distruggere lo stesso giorno.


## 🧹 Pulizia

L'ordine conta: il Network Load Balancer creato da Kubernetes va tolto **prima** del cluster, altrimenti resta acceso (e a pagamento) senza nessuno che lo gestisca.
```bash
kubectl delete -f k8s/springboot-k8s.yaml      # toglie il Network Load Balancer
kubectl delete secret mysql
cdk destroy
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk27eks --query "ResourceTagMappingList[].ResourceARN" --output text
# load balancer rimasti nella VPC (la lista deve essere vuota)
aws elbv2 describe-load-balancers --query "LoadBalancers[?VpcId=='$DEFAULT_VPC'].[LoadBalancerName,Type]" --output table
```
- il database si cancella **senza snapshot finale** e senza backup automatici; il segreto creato da RDS si cancella con il database
- il log group del control plane è dello stack e si cancella con lui
- i security group creati da Kubernetes per il load balancer si cancellano insieme al Service; se `cdk destroy` fallisce sul cluster per un'interfaccia di rete ancora in uso, aspettare qualche minuto e rilanciarlo
- il bootstrap resta (condiviso con gli altri progetti CDK): `../bootstrap/bootstrap.sh destroy <region>` quando nella region non ci sono più stack CDK


## 🚀 Sviluppi Futuri
- 📦 **Immagine su ECR** (repository del cdk23) al posto di Docker Hub
- ⚖️ **AWS Load Balancer Controller** con un Ingress e un Application Load Balancer, con **EKS Pod Identity** per i permessi
- 🤖 **EKS Auto Mode** (`compute_config`) al posto del node group gestito
- 🔐 **Secrets Store CSI Driver** per leggere la password di RDS direttamente da Secrets Manager, senza copiarla in un Secret


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

