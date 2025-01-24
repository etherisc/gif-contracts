import os
from onepassword.client import Client
from onepassword import ItemCreateParams, ItemCategory, ItemSection, ItemField, ItemFieldType

client = None
lastItem = None


async def signIn():
    global client
    # Gets your service account token from the OP_SERVICE_ACCOUNT_TOKEN environment variable.
    token = os.getenv("OP_SERVICE_ACCOUNT_TOKEN")
    # print(token)
    # Connects to 1Password. Fill in your own integration name and version.
    client = await Client.authenticate(auth=token, integration_name="Test", integration_version="v1.0.0")


async def listVaults():
    vaults = await client.vaults.list_all()
    async for vault in vaults:
        print(vault.title, vault.id)


async def getVaultId(vault):
    vaults = await client.vaults.list_all()
    async for v in vaults:
        if v.title == vault:
            return v.id


async def listItems(vault):
    items = await client.items.list_all(await getVaultId(vault))
    async for item in items:
        print(dict(item))


async def getItem(vault, item):
    global lastItem
    vault_id = await getVaultId(vault)
    items = await client.items.list_all(vault_id)
    async for i in items:
        if i.title == item:
            item_id = i.id
            lastItem = await client.items.get(vault_id, item_id)


def getLastItem():
    return lastItem


def getSecret(section, title):
    for s in lastItem.sections:
        if s.title == section:
            for f in lastItem.fields:
                if f.section_id == s.id and f.title == title:
                    return f.value
    return None
