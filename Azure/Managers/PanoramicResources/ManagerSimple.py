# app.py
from flask import Flask, render_template, request, redirect, url_for, session
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.mgmt.resource import ResourceManagementClient, SubscriptionClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.sql import SqlManagementClient
from azure.mgmt.web import WebSiteManagementClient
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.mgmt.containerregistry import ContainerRegistryManagementClient
from azure.mgmt.keyvault import KeyVaultManagementClient
from azure.mgmt.cosmosdb import CosmosDBManagementClient
from azure.mgmt.monitor import MonitorManagementClient
from azure.core.exceptions import AzureError
import os

"""
Questo script Flask fornisce una dashboard semplice per visualizzare le risorse Azure. 

Per eseguirlo:
   - installare python3 e pip3
   - installare le librerie flask e azure-sdk con il requirements.txt
        pip3 install -r requirements.txt
            eventualmente anche con il break-system-packages nei sistemi debian che lo richiedono:
        pip3 install -r requirements.txt --break-system-packages
   - configurare le credenziali Azure (az login oppure variabili d'ambiente)
   - lanciare lo script:
        python3 ManagerSimple.py

"""

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-azure'  # Cambia con una chiave segreta sicura

def get_azure_credential():
    """
    Restituisce le credenziali Azure usando DefaultAzureCredential
    """
    try:
        credential = DefaultAzureCredential()
        return credential
    except Exception as e:
        print(f"Errore nell'ottenere le credenziali Azure: {e}")
        return None

def get_subscriptions():
    """
    Restituisce la lista delle subscription Azure disponibili
    """
    try:
        credential = get_azure_credential()
        if not credential:
            return []
        
        subscription_client = SubscriptionClient(credential)
        subscriptions = list(subscription_client.subscriptions.list())
        return [{'id': sub.subscription_id, 'name': sub.display_name} for sub in subscriptions]
    except Exception as e:
        print(f"Errore nel recupero delle subscription: {e}")
        return []

def get_azure_clients(subscription_id=None):
    """
    Crea i client Azure con la subscription specificata
    """
    if not subscription_id:
        subscription_id = session.get('azure_subscription')
    
    if not subscription_id:
        # Prova a prendere la prima subscription disponibile
        subscriptions = get_subscriptions()
        if subscriptions:
            subscription_id = subscriptions[0]['id']
            session['azure_subscription'] = subscription_id
    
    try:
        credential = get_azure_credential()
        if not credential:
            return None, subscription_id
        
        clients = {
            'resource': ResourceManagementClient(credential, subscription_id),
            'compute': ComputeManagementClient(credential, subscription_id),
            'network': NetworkManagementClient(credential, subscription_id),
            'storage': StorageManagementClient(credential, subscription_id),
            'sql': SqlManagementClient(credential, subscription_id),
            'web': WebSiteManagementClient(credential, subscription_id),
            'container_instance': ContainerInstanceManagementClient(credential, subscription_id),
            'container_registry': ContainerRegistryManagementClient(credential, subscription_id),
            'keyvault': KeyVaultManagementClient(credential, subscription_id),
            'cosmosdb': CosmosDBManagementClient(credential, subscription_id),
            'monitor': MonitorManagementClient(credential, subscription_id)
        }
        return clients, subscription_id
    except Exception as e:
        print(f"Errore nella creazione dei client Azure: {e}")
        return None, subscription_id

def get_azure_resources():
    """
    Recupera le informazioni su varie risorse Azure
    """
    clients, current_subscription = get_azure_clients()
    
    if not clients:
        return {
            'error': 'Impossibile creare i client Azure. Verificare le credenziali (eseguire: az login).',
            'current_subscription': current_subscription
        }
    
    resources = {
        'current_subscription': current_subscription
    }

    # --- 1. Resource Groups ---
    try:
        resource_groups = list(clients['resource'].resource_groups.list())
        resources['resource_groups'] = [
            {
                'name': rg.name,
                'location': rg.location,
                'id': rg.id
            } for rg in resource_groups
        ]
    except Exception as e:
        print(f"Errore nel recupero dei Resource Groups: {e}")
        resources['resource_groups'] = []

    # --- 2. Virtual Machines ---
    try:
        vms = list(clients['compute'].virtual_machines.list_all())
        resources['virtual_machines'] = [
            {
                'name': vm.name,
                'location': vm.location,
                'vm_size': vm.hardware_profile.vm_size,
                'os_type': vm.storage_profile.os_disk.os_type,
                'resource_group': vm.id.split('/')[4]
            } for vm in vms
        ]
    except Exception as e:
        print(f"Errore nel recupero delle Virtual Machines: {e}")
        resources['virtual_machines'] = []

    # --- 3. Virtual Networks ---
    try:
        vnets = list(clients['network'].virtual_networks.list_all())
        resources['virtual_networks'] = [
            {
                'name': vnet.name,
                'location': vnet.location,
                'address_space': vnet.address_space.address_prefixes if vnet.address_space else [],
                'resource_group': vnet.id.split('/')[4]
            } for vnet in vnets
        ]
    except Exception as e:
        print(f"Errore nel recupero delle Virtual Networks: {e}")
        resources['virtual_networks'] = []

    # --- 4. Storage Accounts ---
    try:
        storage_accounts = list(clients['storage'].storage_accounts.list())
        resources['storage_accounts'] = [
            {
                'name': sa.name,
                'location': sa.location,
                'sku': sa.sku.name,
                'kind': sa.kind,
                'resource_group': sa.id.split('/')[4]
            } for sa in storage_accounts
        ]
    except Exception as e:
        print(f"Errore nel recupero degli Storage Accounts: {e}")
        resources['storage_accounts'] = []

    # --- 5. SQL Databases ---
    try:
        sql_servers = list(clients['sql'].servers.list())
        resources['sql_servers'] = []
        resources['sql_databases'] = []
        
        for server in sql_servers:
            rg_name = server.id.split('/')[4]
            resources['sql_servers'].append({
                'name': server.name,
                'location': server.location,
                'version': server.version,
                'resource_group': rg_name
            })
            
            try:
                databases = list(clients['sql'].databases.list_by_server(rg_name, server.name))
                for db in databases:
                    if db.name != 'master':  # Escludi il database di sistema
                        resources['sql_databases'].append({
                            'name': db.name,
                            'server': server.name,
                            'location': db.location,
                            'resource_group': rg_name
                        })
            except:
                pass
    except Exception as e:
        print(f"Errore nel recupero dei SQL Servers/Databases: {e}")
        resources['sql_servers'] = []
        resources['sql_databases'] = []

    # --- 6. App Services ---
    try:
        app_services = list(clients['web'].web_apps.list())
        resources['app_services'] = [
            {
                'name': app.name,
                'location': app.location,
                'state': app.state,
                'default_host_name': app.default_host_name,
                'resource_group': app.id.split('/')[4]
            } for app in app_services
        ]
    except Exception as e:
        print(f"Errore nel recupero degli App Services: {e}")
        resources['app_services'] = []

    # --- 7. Container Instances ---
    try:
        container_groups = list(clients['container_instance'].container_groups.list())
        resources['container_instances'] = [
            {
                'name': cg.name,
                'location': cg.location,
                'os_type': cg.os_type,
                'state': cg.provisioning_state,
                'resource_group': cg.id.split('/')[4]
            } for cg in container_groups
        ]
    except Exception as e:
        print(f"Errore nel recupero dei Container Instances: {e}")
        resources['container_instances'] = []

    # --- 8. Container Registries ---
    try:
        registries = list(clients['container_registry'].registries.list())
        resources['container_registries'] = [
            {
                'name': reg.name,
                'location': reg.location,
                'sku': reg.sku.name,
                'login_server': reg.login_server,
                'resource_group': reg.id.split('/')[4]
            } for reg in registries
        ]
    except Exception as e:
        print(f"Errore nel recupero dei Container Registries: {e}")
        resources['container_registries'] = []

    # --- 9. Key Vaults ---
    try:
        key_vaults = list(clients['keyvault'].vaults.list())
        resources['key_vaults'] = [
            {
                'name': kv.name,
                'location': kv.location,
                'vault_uri': kv.properties.vault_uri,
                'resource_group': kv.id.split('/')[4]
            } for kv in key_vaults
        ]
    except Exception as e:
        print(f"Errore nel recupero dei Key Vaults: {e}")
        resources['key_vaults'] = []

    # --- 10. Cosmos DB Accounts ---
    try:
        cosmos_accounts = list(clients['cosmosdb'].database_accounts.list())
        resources['cosmos_accounts'] = [
            {
                'name': account.name,
                'location': account.location,
                'kind': account.kind,
                'resource_group': account.id.split('/')[4]
            } for account in cosmos_accounts
        ]
    except Exception as e:
        print(f"Errore nel recupero dei Cosmos DB Accounts: {e}")
        resources['cosmos_accounts'] = []

    # --- 11. Network Security Groups ---
    try:
        nsgs = list(clients['network'].network_security_groups.list_all())
        resources['network_security_groups'] = [
            {
                'name': nsg.name,
                'location': nsg.location,
                'resource_group': nsg.id.split('/')[4]
            } for nsg in nsgs
        ]
    except Exception as e:
        print(f"Errore nel recupero dei Network Security Groups: {e}")
        resources['network_security_groups'] = []

    # --- 12. Public IP Addresses ---
    try:
        public_ips = list(clients['network'].public_ip_addresses.list_all())
        resources['public_ips'] = [
            {
                'name': pip.name,
                'location': pip.location,
                'ip_address': pip.ip_address,
                'resource_group': pip.id.split('/')[4]
            } for pip in public_ips
        ]
    except Exception as e:
        print(f"Errore nel recupero dei Public IP Addresses: {e}")
        resources['public_ips'] = []

    return resources

@app.route('/')
def index():
    subscriptions = get_subscriptions()
    azure_data = get_azure_resources()
    return render_template('index.html', 
                         azure_data=azure_data, 
                         subscriptions=subscriptions)

@app.route('/update_settings', methods=['POST'])
def update_settings():
    subscription_id = request.form.get('subscription')
    if subscription_id:
        session['azure_subscription'] = subscription_id
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Per eseguire l'app in modalità sviluppo
    # Assicurati di aver eseguito 'az login' o di avere le credenziali configurate
    app.run(debug=True, host='0.0.0.0', port=5043)
