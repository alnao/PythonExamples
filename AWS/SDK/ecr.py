import boto3
from typing import List, Dict, Optional
from botocore.exceptions import ClientError
import logging

class AwsEcr:
    """
    Classe per gestire le operazioni su Amazon Elastic Container Registry (ECR)
    """
    def __init__(self, profile_name, region_name: str = 'eu-west-1'):

        """
        Inizializza il client ECR
        
        Args:
            aws_profile: AWS profile name (optional)
            region_name: AWS region name
        """
        self.profile_name=profile_name
        boto3.setup_default_session(profile_name=self.profile_name)
        self.logger = logging.getLogger(__name__)
        session = boto3.Session(profile_name=profile_name, region_name=region_name)
        self.ecr_client = session.client('ecr')

    def create_repository(self, repository_name: str, image_tag_mutability: str = 'MUTABLE') -> Dict:
        """
        Crea un nuovo repository ECR
        
        Args:
            repository_name: Nome del repository
            image_tag_mutability: MUTABLE o IMMUTABLE
            
        Returns:
            Dict con i dettagli del repository creato
        """
        try:
            response = self.ecr_client.create_repository(
                repositoryName=repository_name,
                imageTagMutability=image_tag_mutability,
                imageScanningConfiguration={
                    'scanOnPush': True
                }
            )
            self.logger.info(f"Repository {repository_name} creato con successo")
            return response['repository']
        except ClientError as e:
            self.logger.error(f"Errore nella creazione del repository: {e}")
            raise

    def list_repositories(self) -> List[Dict]:
        """
        Lista tutti i repository ECR
        
        Returns:
            Lista di dizionari contenenti i dettagli dei repository
        """
        try:
            response = self.ecr_client.describe_repositories()
            return response['repositories']
        except ClientError as e:
            self.logger.error(f"Errore nel recupero dei repository: {e}")
            raise

    def delete_repository(self, repository_name: str, force: bool = False) -> Dict:
        """
        Elimina un repository ECR
        
        Args:
            repository_name: Nome del repository da eliminare
            force: Se True, elimina il repository anche se contiene immagini
            
        Returns:
            Dict con i dettagli dell'operazione
        """
        try:
            response = self.ecr_client.delete_repository(
                repositoryName=repository_name,
                force=force
            )
            self.logger.info(f"Repository {repository_name} eliminato con successo")
            return response['repository']
        except ClientError as e:
            self.logger.error(f"Errore nell'eliminazione del repository: {e}")
            raise

    def list_images(self, repository_name: str) -> List[Dict]:
        """
        Lista tutte le immagini in un repository
        
        Args:
            repository_name: Nome del repository
            
        Returns:
            Lista di dizionari contenenti i dettagli delle immagini
        """
        try:
            response = self.ecr_client.list_images(repositoryName=repository_name)
            return response['imageIds']
        except ClientError as e:
            self.logger.error(f"Errore nel recupero delle immagini: {e}")
            raise

    def get_authorization_token(self) -> Dict:
        """
        Ottiene il token di autorizzazione per il login Docker
        
        Returns:
            Dict contenente le credenziali di autorizzazione
        """
        try:
            response = self.ecr_client.get_authorization_token()
            return response['authorizationData'][0]
        except ClientError as e:
            self.logger.error(f"Errore nel recupero del token di autorizzazione: {e}")
            raise

    def set_lifecycle_policy(self, repository_name: str, policy: Dict) -> Dict:
        """
        Imposta una lifecycle policy per un repository
        
        Args:
            repository_name: Nome del repository
            policy: Dizionario contenente la policy
            
        Returns:
            Dict con i dettagli dell'operazione
        """
        try:
            response = self.ecr_client.put_lifecycle_policy(
                repositoryName=repository_name,
                lifecyclePolicyText=str(policy)
            )
            self.logger.info(f"Lifecycle policy impostata per {repository_name}")
            return response
        except ClientError as e:
            self.logger.error(f"Errore nell'impostazione della lifecycle policy: {e}")
            raise

def main(profile):
    print("Aws Py Console - Aws ECR START")
    print("-----")
    o = AwsEcr(profile)
    l=list(o.list_repositories())
    for e in l:
        print(e)
        #{'repositoryArn': 'arn:aws:ecr:eu-west-1:740456629644:repository/esempio23-ecr-repository', 
        # 'registryId': '740456629644', 'repositoryName': 'esempio23-ecr-repository', 
        # 'repositoryUri': '740456629644.dkr.ecr.eu-west-1.amazonaws.com/esempio23-ecr-repository',
        #  'createdAt': datetime.datetime(2024, 11, 18, 10, 7, 6, 120000, tzinfo=tzlocal()), 
        # 'imageTagMutability': 'MUTABLE', 'imageScanningConfiguration': {'scanOnPush': True}, 
        # 'encryptionConfiguration': {'encryptionType': 'AES256'}}
    if len(l)>0:
        print("-----")
        ll=list (o.list_images(l[0]['repositoryName'] ))
        for e in ll:
            print(e)
    print("-----")

if __name__ == '__main__':
    main("default")
