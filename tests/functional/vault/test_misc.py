import pytest
import brownie


@pytest.fixture
def other_token(gov, Token):
    yield gov.deploy(Token)


def test_regular_available_deposit_limit(Vault, token, gov):
    vault = gov.deploy(Vault)
    vault.initialize(
        token, gov, gov, token.symbol() + " yVault", "yv" + token.symbol(), gov
    )
    token.approve(vault, 100, {"from": gov})
    vault.setDepositLimit(100)

    vault.deposit(50, {"from": gov})
    assert vault.availableDepositLimit() == 50

    vault.deposit(50, {"from": gov})
    assert vault.availableDepositLimit() == 0


def test_negative_available_deposit_limit(Vault, token, gov):
    vault = gov.deploy(Vault)
    vault.initialize(
        token, gov, gov, token.symbol() + " yVault", "yv" + token.symbol(), gov
    )
    token.approve(vault, 100, {"from": gov})
    vault.setDepositLimit(100)

    vault.deposit(100, {"from": gov})
    assert vault.availableDepositLimit() == 0

    vault.setDepositLimit(50)
    assert vault.availableDepositLimit() == 0


def test_sweep(gov, vault, rando, token, other_token):
    token.transfer(vault, token.balanceOf(gov), {"from": gov})
    other_token.transfer(vault, other_token.balanceOf(gov), {"from": gov})

    # Vault wrapped token doesn't work
    assert token.address == vault.token()
    assert token.balanceOf(vault) > 0
    with brownie.reverts():
        vault.sweep(token, {"from": gov})

    # But any other random token works
    assert other_token.address != vault.token()
    assert other_token.balanceOf(vault) > 0
    assert other_token.balanceOf(gov) == 0
    # Not any random person can do this
    with brownie.reverts():
        vault.sweep(other_token, {"from": rando})

    before = other_token.balanceOf(vault)
    vault.sweep(other_token, 1, {"from": gov})
    assert other_token.balanceOf(vault) == before - 1
    assert other_token.balanceOf(gov) == 1
    vault.sweep(other_token, {"from": gov})
    assert other_token.balanceOf(vault) == 0
    assert other_token.balanceOf(gov) == before
    assert other_token.balanceOf(rando) == 0


def test_reject_ether(gov, vault):
    # These functions should reject any calls with value
    for func, args in [
        ("setGovernance", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"]),
        ("setManagement", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"]),
        ("acceptGovernance", []),
        ("setRewards", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"]),
        ("setGuardian", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"]),
        ("setPerformanceFee", [0]),
        ("setManagementFee", [0]),
        ("setEmergencyShutdown", [True]),
        ("approve", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", 1]),
        ("transfer", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", 1]),
        (
            "transferFrom",
            [
                "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                1,
            ],
        ),
        ("deposit", []),
        ("withdraw", []),
        ("deposit", [1]),
        ("withdraw", [1]),
        ("deposit", [1, "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"]),
        ("withdraw", [1, "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"]),
        ("addStrategy", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", 1, 1, 1, 1]),
        ("addStrategyToQueue", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"]),
        ("removeStrategyFromQueue", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"]),
        ("updateStrategyDebtRatio", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", 1]),
        (
            "updateStrategyMinDebtPerHarvest",
            ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", 1],
        ),
        (
            "updateStrategyMaxDebtPerHarvest",
            ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", 1],
        ),
        (
            "updateStrategyPerformanceFee",
            ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", 1],
        ),
        (
            "migrateStrategy",
            [
                "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            ],
        ),
        ("revokeStrategy", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"]),
        ("report", [1, 2, 3]),
        ("sweep", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"]),
        ("sweep", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", 1]),
    ]:
        with brownie.reverts("Cannot send ether to nonpayable function"):
            # NOTE: gov can do anything
            getattr(vault, func)(*args, {"from": gov, "value": 1})

    # Fallback fails too
    with brownie.reverts("Cannot send ether to nonpayable function"):
        gov.transfer(vault, 1)

    # NOTE: Just for coverage
    with brownie.reverts():
        gov.transfer(vault, 0)


def test_deposit_withdraw_faillure(token, gov, vault):
    token._setBlocked(vault.address, True, {"from": gov})
    with brownie.reverts():
        vault.deposit({"from": gov})

    token._setBlocked(vault.address, False, {"from": gov})
    token.approve(vault, 2 ** 256 - 1, {"from": gov})
    vault.deposit({"from": gov})
    token._setBlocked(gov, True, {"from": gov})

    with brownie.reverts():
        vault.withdraw(vault.balanceOf(gov), {"from": gov})


def test_report_loss(token, gov, vault, strategy, accounts):
    strategy.harvest()
    strategy._takeFunds(token.balanceOf(strategy), {"from": gov})
    assert token.balanceOf(strategy) == 0

    # Make sure we do not send more funds to the strategy.
    strategy.harvest()
    assert token.balanceOf(strategy) == 0

    assert vault.debtRatio() == 0
