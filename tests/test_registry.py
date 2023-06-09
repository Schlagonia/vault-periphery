import ape
from ape import project, chain
from utils.constants import WEEK, ZERO_ADDRESS
import pytest


def add_new_release(release_registry, factory, owner):
    txs = release_registry.newRelease(factory.address, sender=owner)

    event = list(txs.decode_logs(release_registry.NewRelease))

    assert len(event) == 1
    assert event[0].factory == factory
    assert event[0].apiVersion == factory.api_version()


def test__set_up(registry, asset, release_registry, daddy):
    assert registry.governance() == daddy
    assert registry.releaseRegistry() == release_registry
    assert registry.numAssets() == 0
    assert registry.numEndorsedVaults(asset) == 0
    assert registry.numEndorsedStrategies(asset) == 0


def test__deploy_new_vault(registry, asset, release_registry, vault_factory, daddy):
    # Add the factory as the first release
    add_new_release(
        release_registry=release_registry, factory=vault_factory, owner=daddy
    )

    assert release_registry.numReleases() == 1

    name = "New vaults"
    symbol = "yvTest"

    # Deploy a new vault
    tx = registry.newEndorsedVault(asset, name, symbol, daddy, WEEK, 0, sender=daddy)

    # address = tx.return_value
    # new_vault = project.dependencies["yearn-vaults"]["master"].VaultV3.at(address)
    block = tx.timestamp

    event = list(tx.decode_logs(registry.NewEndorsedVault))
    new_vault = project.dependencies["yearn-vaults"]["master"].VaultV3.at(
        event[0].vault
    )

    assert len(event) == 1
    assert event[0].asset == asset.address
    assert event[0].vault == new_vault
    assert event[0].releaseVersion == 0

    # make sure the vault is set up correctly
    assert new_vault.name() == name
    assert new_vault.symbol() == symbol
    assert new_vault.role_manager() == daddy
    assert new_vault.profitMaxUnlockTime() == WEEK

    # Make sure it was endorsed correctly
    assert registry.numAssets() == 1
    assert registry.getAssets()[0] == asset.address
    assert registry.numEndorsedVaults(asset) == 1
    assert registry.numEndorsedVaultsByVersion(asset, 0) == 1
    assert registry.getEndorsedVaults(asset)[0] == new_vault.address
    assert registry.getEndorsedVaultsByVersion(asset, 0)[0] == new_vault.address
    all_vaults = registry.getAllEndorsedVaults()
    assert len(all_vaults) == 1
    assert len(all_vaults[0]) == 1
    assert all_vaults[0][0] == new_vault.address
    assert registry.info(new_vault.address).asset == asset.address
    assert registry.info(new_vault.address).releaseVersion == 0
    assert registry.info(new_vault.address).deploymentTimeStamp == block


def test__endorse_deployed_vault(
    registry, asset, release_registry, vault_factory, daddy
):
    # Add the factory as the first release
    add_new_release(
        release_registry=release_registry, factory=vault_factory, owner=daddy
    )

    assert release_registry.numReleases() == 1

    name = "New vaults"
    symbol = "yvTest"

    # Deploy a new vault
    tx = vault_factory.deploy_new_vault(asset, name, symbol, daddy, WEEK, sender=daddy)

    block = tx.timestamp

    event = list(tx.decode_logs(vault_factory.NewVault))
    new_vault = project.dependencies["yearn-vaults"]["master"].VaultV3.at(
        event[0].vault_address
    )

    # Endorse vault
    registry.endorseVault(new_vault.address, 0, block, sender=daddy)

    # Make sure it was endorsed correctly
    assert registry.numAssets() == 1
    assert registry.getAssets()[0] == asset.address
    assert registry.numEndorsedVaults(asset) == 1
    assert registry.numEndorsedVaultsByVersion(asset, 0) == 1
    assert registry.getEndorsedVaults(asset)[0] == new_vault.address
    assert registry.getEndorsedVaultsByVersion(asset, 0)[0] == new_vault.address
    all_vaults = registry.getAllEndorsedVaults()
    assert len(all_vaults) == 1
    assert len(all_vaults[0]) == 1
    assert all_vaults[0][0] == new_vault.address
    assert registry.info(new_vault.address).asset == asset.address
    assert registry.info(new_vault.address).releaseVersion == 0
    assert registry.info(new_vault.address).deploymentTimeStamp == block


def test__endorse_deployed_vault__default_values(
    registry, asset, release_registry, vault_factory, daddy
):
    # Add the factory as the first release
    add_new_release(
        release_registry=release_registry, factory=vault_factory, owner=daddy
    )

    assert release_registry.numReleases() == 1

    name = "New vaults"
    symbol = "yvTest"

    # Deploy a new vault
    tx = vault_factory.deploy_new_vault(asset, name, symbol, daddy, WEEK, sender=daddy)

    event = list(tx.decode_logs(vault_factory.NewVault))
    new_vault = project.dependencies["yearn-vaults"]["master"].VaultV3.at(
        event[0].vault_address
    )

    # Endorse vault
    registry.endorseVault(new_vault.address, sender=daddy)

    # Make sure it was endorsed correctly
    assert registry.numAssets() == 1
    assert registry.getAssets()[0] == asset.address
    assert registry.numEndorsedVaults(asset) == 1
    assert registry.numEndorsedVaultsByVersion(asset, 0) == 1
    assert registry.getEndorsedVaults(asset)[0] == new_vault.address
    assert registry.getEndorsedVaultsByVersion(asset, 0)[0] == new_vault.address
    all_vaults = registry.getAllEndorsedVaults()
    assert len(all_vaults) == 1
    assert len(all_vaults[0]) == 1
    assert all_vaults[0][0] == new_vault.address
    assert registry.info(new_vault.address).asset == asset.address
    assert registry.info(new_vault.address).releaseVersion == 0
    assert registry.info(new_vault.address).deploymentTimeStamp == 0


def test__endorse_deployed_strategy(
    registry, asset, release_registry, vault_factory, strategy, daddy, chain
):
    # Add the factory as the first release
    add_new_release(
        release_registry=release_registry, factory=vault_factory, owner=daddy
    )

    block = chain.pending_timestamp - 1
    tx = registry.endorseStrategy(strategy, 0, block, sender=daddy)

    event = list(tx.decode_logs(registry.NewEndorsedStrategy))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].asset == asset.address
    assert event[0].releaseVersion == 0

    # Make sure it was endorsed correctly
    assert registry.numAssets() == 1
    assert registry.getAssets()[0] == asset.address
    assert registry.numEndorsedStrategies(asset) == 1
    assert registry.numEndorsedStrategiesByVersion(asset, 0) == 1
    assert registry.getEndorsedStrategies(asset)[0] == strategy.address
    assert registry.getEndorsedStrategiesByVersion(asset, 0)[0] == strategy.address
    all_strategies = registry.getAllEndorsedStrategies()
    assert len(all_strategies) == 1
    assert len(all_strategies[0]) == 1
    assert all_strategies[0][0] == strategy.address
    assert registry.info(strategy.address).asset == asset.address
    assert registry.info(strategy.address).releaseVersion == 0
    assert registry.info(strategy.address).deploymentTimeStamp == block


def test__endorse_deployed_strategy__default_values(
    registry, asset, release_registry, vault_factory, strategy, daddy, chain
):
    # Add the factory as the first release
    add_new_release(
        release_registry=release_registry, factory=vault_factory, owner=daddy
    )

    tx = registry.endorseStrategy(strategy, sender=daddy)

    event = list(tx.decode_logs(registry.NewEndorsedStrategy))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].asset == asset.address
    assert event[0].releaseVersion == 0

    # Make sure it was endorsed correctly
    assert registry.numAssets() == 1
    assert registry.getAssets()[0] == asset.address
    assert registry.numEndorsedStrategies(asset) == 1
    assert registry.numEndorsedStrategiesByVersion(asset, 0) == 1
    assert registry.getEndorsedStrategies(asset)[0] == strategy.address
    assert registry.getEndorsedStrategiesByVersion(asset, 0)[0] == strategy.address
    all_strategies = registry.getAllEndorsedStrategies()
    assert len(all_strategies) == 1
    assert len(all_strategies[0]) == 1
    assert all_strategies[0][0] == strategy.address
    assert registry.info(strategy.address).asset == asset.address
    assert registry.info(strategy.address).releaseVersion == 0
    assert registry.info(strategy.address).deploymentTimeStamp == 0


def test__deploy_vault_with_new_release(
    registry, asset, release_registry, vault_factory, daddy
):
    # Add a mock factory for version release 1
    mock_factory = daddy.deploy(project.MockFactory, "6.9")
    add_new_release(
        release_registry=release_registry, factory=mock_factory, owner=daddy
    )

    assert release_registry.numReleases() == 1

    # Set the factory as the second release
    add_new_release(
        release_registry=release_registry, factory=vault_factory, owner=daddy
    )

    assert release_registry.numReleases() == 2

    name = "New vaults"
    symbol = "yvTest"

    # Deploy a new vault
    tx = registry.newEndorsedVault(asset, name, symbol, daddy, WEEK, 0, sender=daddy)

    # address = tx.return_value
    # new_vault = project.dependencies["yearn-vaults"]["master"].VaultV3.at(address)
    block = tx.timestamp

    event = list(tx.decode_logs(registry.NewEndorsedVault))
    new_vault = project.dependencies["yearn-vaults"]["master"].VaultV3.at(
        event[0].vault
    )

    assert len(event) == 1
    assert event[0].asset == asset.address
    assert event[0].vault == new_vault
    assert event[0].releaseVersion == 1

    # make sure the vault is set up correctly
    assert new_vault.name() == name
    assert new_vault.symbol() == symbol
    assert new_vault.role_manager() == daddy
    assert new_vault.profitMaxUnlockTime() == WEEK

    # Make sure it was endorsed correctly
    assert registry.numAssets() == 1
    assert registry.getAssets()[0] == asset.address
    assert registry.numEndorsedVaults(asset) == 1
    assert registry.numEndorsedVaultsByVersion(asset, 0) == 1
    assert registry.getEndorsedVaults(asset)[0] == new_vault.address
    assert registry.getEndorsedVaultsByVersion(asset, 0)[0] == new_vault.address
    all_vaults = registry.getAllEndorsedVaults()
    assert len(all_vaults) == 1
    assert len(all_vaults[0]) == 1
    assert all_vaults[0][0] == new_vault.address
    assert registry.info(new_vault.address).asset == asset.address
    assert registry.info(new_vault.address).releaseVersion == 1
    assert registry.info(new_vault.address).deploymentTimeStamp == block


def test__deploy_vault_with_oldrelease(
    registry, asset, release_registry, vault_factory, daddy
):
    # Set the factory as the first release
    add_new_release(
        release_registry=release_registry, factory=vault_factory, owner=daddy
    )

    assert release_registry.numReleases() == 1

    # Add a mock factory for version release 2
    mock_factory = daddy.deploy(project.MockFactory, "6.9")
    add_new_release(
        release_registry=release_registry, factory=mock_factory, owner=daddy
    )

    assert release_registry.numReleases() == 2

    name = "New vaults"
    symbol = "yvTest"

    # Deploy a new vault offset of 1
    tx = registry.newEndorsedVault(asset, name, symbol, daddy, WEEK, 1, sender=daddy)

    # address = tx.return_value
    # new_vault = project.dependencies["yearn-vaults"]["master"].VaultV3.at(address)
    block = tx.timestamp

    event = list(tx.decode_logs(registry.NewEndorsedVault))
    new_vault = project.dependencies["yearn-vaults"]["master"].VaultV3.at(
        event[0].vault
    )

    assert len(event) == 1
    assert event[0].asset == asset.address
    assert event[0].vault == new_vault
    assert event[0].releaseVersion == 0

    # make sure the vault is set up correctly
    assert new_vault.name() == name
    assert new_vault.symbol() == symbol
    assert new_vault.role_manager() == daddy
    assert new_vault.profitMaxUnlockTime() == WEEK

    # Make sure it was endorsed correctly
    assert registry.numAssets() == 1
    assert registry.getAssets()[0] == asset.address
    assert registry.numEndorsedVaults(asset) == 1
    assert registry.numEndorsedVaultsByVersion(asset, 1) == 1
    assert registry.getEndorsedVaults(asset)[0] == new_vault.address
    assert registry.getEndorsedVaultsByVersion(asset, 1)[0] == new_vault.address
    all_vaults = registry.getAllEndorsedVaults()
    assert len(all_vaults) == 1
    assert len(all_vaults[0]) == 1
    assert all_vaults[0][0] == new_vault.address
    assert registry.info(new_vault.address).asset == asset.address
    assert registry.info(new_vault.address).releaseVersion == 0
    assert registry.info(new_vault.address).deploymentTimeStamp == block


def test__endorse_deployed_vault_wrong_api__reverts(
    registry, asset, release_registry, vault_factory, daddy
):
    # Add a mock factory for version release 1
    mock_factory = daddy.deploy(project.MockFactory, "6.9")
    add_new_release(
        release_registry=release_registry, factory=mock_factory, owner=daddy
    )

    assert release_registry.numReleases() == 1

    # Set the factory as the second release
    add_new_release(
        release_registry=release_registry, factory=vault_factory, owner=daddy
    )

    assert release_registry.numReleases() == 2

    name = "New vaults"
    symbol = "yvTest"

    # Deploy a new vault
    tx = vault_factory.deploy_new_vault(asset, name, symbol, daddy, WEEK, sender=daddy)

    event = list(tx.decode_logs(vault_factory.NewVault))
    new_vault = project.dependencies["yearn-vaults"]["master"].VaultV3.at(
        event[0].vault_address
    )

    # Endorse vault with incorrect api version
    with ape.reverts("Wrong API Version"):
        registry.endorseVault(new_vault, 1, 0, sender=daddy)

    registry.endorseVault(new_vault, 0, 0, sender=daddy)


def test__endorse_strategy_wrong_api__reverts(
    registry, asset, strategy, release_registry, vault_factory, daddy
):
    # Add a mock factory for version release 1
    mock_factory = daddy.deploy(project.MockFactory, "6.9")
    add_new_release(
        release_registry=release_registry, factory=mock_factory, owner=daddy
    )

    assert release_registry.numReleases() == 1

    # Set the factory as the second release
    add_new_release(
        release_registry=release_registry, factory=vault_factory, owner=daddy
    )

    assert release_registry.numReleases() == 2

    # Endorse vault with incorrect api version
    with ape.reverts("Wrong API Version"):
        registry.endorseStrategy(strategy, 1, 0, sender=daddy)

    registry.endorseStrategy(strategy, 0, 0, sender=daddy)


def test__tag_vault(registry, asset, release_registry, vault_factory, daddy, strategy):
    add_new_release(
        release_registry=release_registry, factory=vault_factory, owner=daddy
    )

    assert release_registry.numReleases() == 1

    name = "New vaults"
    symbol = "yvTest"

    # Deploy a new vault offset of 1
    tx = registry.newEndorsedVault(asset, name, symbol, daddy, WEEK, 0, sender=daddy)

    event = list(tx.decode_logs(registry.NewEndorsedVault))
    vault = project.dependencies["yearn-vaults"]["master"].VaultV3.at(event[0].vault)

    # Make sure it is endorsed but not tagged.
    assert registry.info(vault.address).asset == asset.address
    assert registry.info(vault.address).tag == ""

    tag = "Test Tag"

    registry.tagVault(vault.address, tag, sender=daddy)

    assert registry.info(vault.address).asset == asset.address
    assert registry.info(vault.address).tag == tag

    # Try to tag an undendorsed vault
    with ape.reverts("!Endorsed"):
        registry.tagVault(strategy.address, tag, sender=daddy)

    # Endorse the strategy then tag it.
    registry.endorseStrategy(strategy.address, sender=daddy)

    assert registry.info(strategy.address).asset == asset.address
    assert registry.info(strategy.address).tag == ""

    tag = "Test Tag"

    registry.tagVault(strategy.address, tag, sender=daddy)

    assert registry.info(strategy.address).asset == asset.address
    assert registry.info(strategy.address).tag == tag


def test__access(
    registry, asset, release_registry, vault_factory, daddy, strategy, user
):
    add_new_release(
        release_registry=release_registry, factory=vault_factory, owner=daddy
    )

    name = "New vaults"
    symbol = "yvTest"

    # Cant deploy a vault through registry
    with ape.reverts("!governance"):
        registry.newEndorsedVault(asset, name, symbol, daddy, WEEK, 0, sender=user)

    # Deploy a new vault
    tx = vault_factory.deploy_new_vault(asset, name, symbol, daddy, WEEK, sender=daddy)

    event = list(tx.decode_logs(vault_factory.NewVault))
    new_vault = project.dependencies["yearn-vaults"]["master"].VaultV3.at(
        event[0].vault_address
    )

    # Cant endorse a vault
    with ape.reverts("!governance"):
        registry.endorseVault(new_vault, 0, 0, sender=user)

    # cant endorse vault with default values
    with ape.reverts("!governance"):
        registry.endorseVault(new_vault, sender=user)

    # cant endorse strategy
    with ape.reverts("!governance"):
        registry.endorseStrategy(strategy, 0, 0, sender=user)

    # cant endorse strategy with default values
    with ape.reverts("!governance"):
        registry.endorseStrategy(strategy, sender=user)

    with ape.reverts("!governance"):
        registry.tagVault(strategy, "tag", sender=user)

    # cant transfer governance
    with ape.reverts("!governance"):
        registry.transferGovernance(user, sender=user)


def test__transfer_governance(registry, daddy, user):
    assert registry.governance() == daddy

    with ape.reverts("ZERO ADDRESS"):
        registry.transferGovernance(ZERO_ADDRESS, sender=daddy)

    assert registry.governance() == daddy

    tx = registry.transferGovernance(user, sender=daddy)

    event = list(tx.decode_logs(registry.GovernanceTransferred))

    assert len(event) == 1
    assert event[0].previousGovernance == daddy
    assert event[0].newGovernance == user
    assert registry.governance() == user
