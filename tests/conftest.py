import pytest
from ape import accounts, project
from utils.constants import MAX_INT, WEEK, ROLES
from web3 import Web3, HTTPProvider
from hexbytes import HexBytes
import os
import time

# we default to local node
w3 = Web3(HTTPProvider(os.getenv("CHAIN_PROVIDER", "http://127.0.0.1:8545")))


@pytest.fixture(scope="session")
def daddy(accounts):
    yield accounts[0]


@pytest.fixture(scope="session")
def management(accounts):
    yield accounts[2]


@pytest.fixture(scope="session")
def fee_recipient(accounts):
    return accounts[3]


@pytest.fixture(scope="session")
def user(accounts):
    return accounts[9]


@pytest.fixture(scope="session")
def create_token(project, daddy, user, amount):
    def create_token(
        name="Test Token", symbol="yTest", initialUser=user, initialAmount=amount
    ):
        token = daddy.deploy(
            project.MockERC20,
            name,
            symbol,
            initialUser,
            initialAmount,
        )

        return token

    yield create_token


@pytest.fixture(scope="session")
def asset(create_token):
    yield create_token()


@pytest.fixture(scope="session")
def amount():
    return int(1_000 * 1e18)


@pytest.fixture(scope="session")
def vault_blueprint(project, daddy):
    blueprint_bytecode = b"\xFE\x71\x00" + HexBytes(
        project.dependencies["yearn-vaults"][
            "master"
        ].VaultV3.contract_type.deployment_bytecode.bytecode
    )  # ERC5202
    len_bytes = len(blueprint_bytecode).to_bytes(2, "big")
    deploy_bytecode = HexBytes(
        b"\x61" + len_bytes + b"\x3d\x81\x60\x0a\x3d\x39\xf3" + blueprint_bytecode
    )

    c = w3.eth.contract(abi=[], bytecode=deploy_bytecode)
    deploy_transaction = c.constructor()
    tx_info = {"from": daddy.address, "value": 0, "gasPrice": 0}
    tx_hash = deploy_transaction.transact(tx_info)

    return w3.eth.get_transaction_receipt(tx_hash)["contractAddress"]


@pytest.fixture(scope="session")
def vault_factory(project, daddy, vault_blueprint):
    vault_factory = daddy.deploy(
        project.dependencies["yearn-vaults"]["master"].VaultFactory,
        "Vault V3 Factory 3.0.1-beta",
        vault_blueprint,
        daddy.address,
    )
    return vault_factory


@pytest.fixture(scope="session")
def release_registry(project, daddy):
    release_registry = daddy.deploy(project.ReleaseRegistry, daddy)

    yield release_registry


@pytest.fixture(scope="session")
def new_registry(daddy, registry_factory):
    def new_registry(gov=daddy):
        tx = registry_factory.createNewRegistry(gov, "New test Registry", sender=gov)
        return project.Registry.at(
            list(tx.decode_logs(registry_factory.NewRegistry))[0].newRegistry
        )

    yield new_registry


@pytest.fixture(scope="session")
def registry_factory(daddy, project, release_registry):
    factory = daddy.deploy(project.RegistryFactory, release_registry)
    yield factory


@pytest.fixture(scope="session")
def registry(new_registry, registry_factory, daddy):
    return new_registry(daddy)


@pytest.fixture(scope="session")
def create_vault(project, daddy, vault_factory):
    def create_vault(
        asset,
        governance=daddy,
        deposit_limit=MAX_INT,
        max_profit_locking_time=WEEK,
        vault_name=None,
        vault_symbol="VV3",
    ):
        vault_suffix = str(int(time.time()))[-4:]
        vault_name = f"Vault V3 {vault_suffix}"

        tx = vault_factory.deploy_new_vault(
            asset,
            vault_name,
            vault_symbol,
            governance,
            max_profit_locking_time,
            sender=daddy,
        )

        event = list(tx.decode_logs(vault_factory.NewVault))
        vault = project.dependencies["yearn-vaults"]["master"].VaultV3.at(
            event[0].vault_address
        )

        vault.set_role(
            daddy.address,
            ROLES.ADD_STRATEGY_MANAGER
            | ROLES.REVOKE_STRATEGY_MANAGER
            | ROLES.FORCE_REVOKE_MANAGER
            | ROLES.ACCOUNTANT_MANAGER
            | ROLES.QUEUE_MANAGER
            | ROLES.REPORTING_MANAGER
            | ROLES.DEBT_MANAGER
            | ROLES.MAX_DEBT_MANAGER
            | ROLES.DEPOSIT_LIMIT_MANAGER
            | ROLES.MINIMUM_IDLE_MANAGER
            | ROLES.PROFIT_UNLOCK_MANAGER
            | ROLES.SWEEPER
            | ROLES.EMERGENCY_MANAGER,
            sender=daddy,
        )

        # set vault deposit
        vault.set_deposit_limit(deposit_limit, sender=daddy)

        return vault

    yield create_vault


@pytest.fixture(scope="session")
def vault(asset, create_vault):
    vault = create_vault(asset)
    yield vault


@pytest.fixture(scope="session")
def create_strategy(project, management, asset):
    def create_strategy(token=asset, apiVersion="3.0.1-beta"):
        strategy = management.deploy(project.MockStrategy, token.address, apiVersion)

        return strategy

    yield create_strategy


@pytest.fixture(scope="session")
def strategy(asset, create_strategy):
    strategy = create_strategy(asset)
    yield strategy


@pytest.fixture(scope="function")
def create_vault_and_strategy(strategy, vault, deposit_into_vault):
    def create_vault_and_strategy(account, amount_into_vault):
        deposit_into_vault(vault, amount_into_vault)
        vault.add_strategy(strategy.address, sender=account)
        return vault, strategy

    yield create_vault_and_strategy


@pytest.fixture(scope="function")
def deposit_into_vault(asset, user):
    def deposit_into_vault(vault, amount_to_deposit):
        asset.approve(vault.address, amount_to_deposit, sender=user)
        vault.deposit(amount_to_deposit, user.address, sender=user)

    yield deposit_into_vault


@pytest.fixture(scope="function")
def provide_strategy_with_debt():
    def provide_strategy_with_debt(account, strategy, vault, target_debt: int):
        vault.update_max_debt_for_strategy(
            strategy.address, target_debt, sender=account
        )
        vault.update_debt(strategy.address, target_debt, sender=account)

    return provide_strategy_with_debt


@pytest.fixture(scope="session")
def deploy_accountant(project, daddy, fee_recipient):
    def deploy_accountant(
        manager=daddy,
        fee_recipient=fee_recipient,
        management_fee=100,
        performance_fee=1_000,
        refund_ratio=0,
        max_fee=0,
    ):
        accountant = daddy.deploy(
            project.GenericAccountant,
            manager,
            fee_recipient,
            management_fee,
            performance_fee,
            refund_ratio,
            max_fee,
        )

        return accountant

    yield deploy_accountant


@pytest.fixture(scope="session")
def accountant(deploy_accountant):
    accountant = deploy_accountant()

    yield accountant


@pytest.fixture(scope="session")
def set_fees_for_strategy():
    def set_fees_for_strategy(
        daddy,
        strategy,
        accountant,
        management_fee,
        performance_fee,
        refund_ratio=0,
        max_fee=0,
    ):
        accountant.set_management_fee(strategy.address, management_fee, sender=daddy)
        accountant.set_performance_fee(strategy.address, performance_fee, sender=daddy)
        accountant.set_refund_ratio(strategy.address, refund_ratio, sender=daddy)
        accountant.set_max_fee(strategy.address, max_fee, sender=daddy)

    return set_fees_for_strategy
