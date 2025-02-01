from brownie import accounts, web3, Contract
from eth_account.messages import encode_typed_data
from eth_account import Account
from eth_utils import to_bytes
from time import time

from scripts.context import context, a, usdc, getHdWallet, multicall
from scripts.prompt import prompt

# Multicall contract, see https://www.multicall3.com/


class FarmerFunding:

    partners = ["Lemonade", "WFP", "Farmer"]
    currencies = ["KES", "USDC"]
    token_spender_names = ["escrow", "treasury"]

    def __init__(self):
        self.usdc_conversion_rate = 130
        self.instanceOperator = a["instanceOperator"]
        self.insurer = a["insurer"]
        self.dry_run = True
        self.token_spenders = [
            getattr(context, spender) for spender in self.token_spender_names
        ]
        self.prompt_parameters()

    def conv_kes_usdc(self, kes):
        return round(kes * 10 ** usdc.decimals() / self.usdc_conversion_rate)

    def set_dry_run(self):
        self.dry_run = prompt.enterBool("Dry run?")

    def prompt_parameters(self):
        self.farmer_count = prompt.enterNumber(
            "Enter the number of farmers",
            default=5052,
            len=42,
        )
        self.farmer_hd_start_index = prompt.enterNumber(
            "Enter the Farmer HD wallet start index",
            default=20000,
            len=42,
        )
        self.escrow_hd_start_index = prompt.enterNumber(
            "Enter the Escrow HD wallet start index",
            default=10,
            len=42,
        )
        self.batch_size = prompt.enterNumber(
            "Enter the batch size for permits",
            default=100,
            len=42,
        )
        self.approval_amount = prompt.enterNumber(
            "Enter the approval amount for permits",
            default=1000 * 10 ** usdc.decimals(),
            len=42,
        )

        self.farmer_hd_last_index = None
        self.farmer_hd_max_index = self.farmer_hd_start_index + self.farmer_count

        self.partnerWallets = {
            partner: {
                "index": index + self.escrow_hd_start_index,
                "wallet": getHdWallet("escrow", index + self.escrow_hd_start_index),
            }
            for index, partner in enumerate(self.partners)
        }

        self.funding = {
            "single": {
                "KES": {
                    "Lemonade": prompt.enterNumber(
                        "Enter the Lemonade funding amount in KES",
                        default=1000,
                        len=42,
                    ),
                    "WFP": prompt.enterNumber(
                        "Enter the WFP funding amount in KES",
                        default=1000,
                        len=42,
                    ),
                    "Farmer": prompt.enterNumber(
                        "Enter the Farmer funding amount in KES",
                        default=500,
                        len=42,
                    ),
                }
            }
        }
        self.funding["single"]["USDC"] = {
            key: self.conv_kes_usdc(value)
            for key, value in self.funding["single"]["KES"].items()
        }
        self.funding["total"] = {
            "farmer": {
                keyCurr: sum(value for value in valueCurr.values())
                for keyCurr, valueCurr in self.funding["single"].items()
            },
            "partner": {
                keyCurr: {
                    keyPartner: value * self.farmer_count
                    for keyPartner, value in valueCurr.items()
                }
                for keyCurr, valueCurr in self.funding["single"].items()
            },
        }

    def print_parameters(self):
        data = self.funding
        """
        Prints a formatted table of the funding parameters.
        """

        # Extracting and processing data
        rows = []

        # Processing 'single' category
        for currency, entities in data["single"].items():
            for entity, value in entities.items():
                rows.append(["single", "", currency, entity, value])

        # Processing 'total' category
        for category, currencies in data["total"].items():
            for currency, entities in currencies.items():
                if isinstance(entities, int):  # Extract value directly
                    rows.append(["total", category, currency, "", entities])
                else:
                    for entity, value in entities.items():
                        rows.append(["total", category, currency, entity, value])

        # Find max widths for each column for alignment
        col_widths = [
            max(
                len(str(row[i]))
                for row in rows
                + [["Category", "Subcategory", "Currency", "Entity", "Value"]]
            )
            for i in range(5)
        ]

        # Print header
        print(
            f"{'Category':<{col_widths[0]}}  {'Subcategory':<{col_widths[1]}}  {'Currency':<{col_widths[2]}}  {'Entity':<{col_widths[3]}}  {'Value':>{col_widths[4]}}"
        )
        print("-" * (sum(col_widths) + 10))  # Line separator

        # Print rows with optimized display (avoiding duplicates)
        prev_category, prev_subcategory, prev_currency = None, None, None
        for category, subcategory, currency, entity, value in rows:
            category_str = (
                category if category != prev_category else ""
            )  # Print only if different
            subcategory_str = (
                subcategory if subcategory != prev_subcategory else ""
            )  # Print only if different
            currency_str = (
                currency if currency != prev_currency else ""
            )  # Print only if different
            print(
                f"{category_str:<{col_widths[0]}}  {subcategory_str:<{col_widths[1]}}  {currency_str:<{col_widths[2]}}  {entity:<{col_widths[3]}}  {value:>{col_widths[4]}}"
            )
            prev_category, prev_subcategory, prev_currency = (
                category,
                subcategory,
                currency,
            )

    def check_parameters(self):
        return (
            all(
                hasattr(self, element)
                for element in [
                    "farmer_count",
                    "farmer_hd_start_index",
                    "escrow_hd_start_index",
                    "funding",
                ]
            )
            and all(
                hasattr(self.funding, keySingleTotal)
                for keySingleTotal in ["single", "total"]
            )
            and all(
                [
                    hasattr(self.funding[keySingleTotal], keyCurr)
                    for keyCurr in self.currencies
                    for keySingleTotal in ["single", "total"]
                ]
            )
            and all(
                [
                    hasattr(
                        self.funding["single"][keyCurr],
                        keyPartner,
                    )
                    for keyPartner in self.partners
                    for keyCurr in self.currencies
                ]
            )
            and all(
                [
                    hasattr(self.funding["total"][keyCurr], keyPartner)
                    for keyCurr in self.currencies
                    for keyPartner in self.partners
                ]
            )
        )

    def fund_escrows(self):
        if self.check_parameters():
            for i in range(
                self.hd_start_index, self.hd_start_index + self.farmer_count
            ):
                pass

        else:
            print("Please set the parameters first.")
            return

    def fund_escrows(self):
        for partner, wallet in self.partnerWallets.items():
            targetFunding = self.funding["total"]["partner"]["USDC"][partner]
            balance = usdc.balanceOf(wallet["wallet"])
            if balance < targetFunding:
                print(
                    f"Insufficient funds in {partner} wallet. Current balance: {balance}, required: {targetFunding}"
                )
                if self.dry_run:
                    print(
                        (
                            f"Dry run: Transfer "
                            f"{targetFunding - balance} USDC to {partner} wallet"
                        )
                    )
                    continue
                usdc.transfer(
                    wallet["wallet"],
                    targetFunding - balance,
                    {"from": self.instanceOperator},
                )
            else:
                print(
                    (
                        f"{partner} wallet has sufficient funds"
                        f" (target = {targetFunding}, balance: {balance})."
                    )
                )

    def approve_escrows(self):
        spender = context.multicallAddress
        for partner, wallet in self.partnerWallets.items():
            targetFunding = self.funding["total"]["partner"]["USDC"][partner]
            print(
                (
                    f"{'Dry run: ' if self.dry_run else ''}Approve {partner} wallet "
                    f"for {targetFunding} USDC to {spender}"
                )
            )
            if self.dry_run:
                continue

            if wallet["wallet"].balance() < 0.05 * 10**18:
                print(f"Insufficient funds in {partner} wallet - funding")
                self.instanceOperator.transfer(wallet["wallet"], 0.05 * 10**18)

            usdc.approve(spender, targetFunding, {"from": wallet["wallet"]})

    # Generate EIP-712 Permit signature
    def get_permit_calldata(self, wallet, spender, amount, nonce, deadline):

        domain = {
            "name": usdc.name(),
            "version": "1",
            "chainId": web3.eth.chain_id,
            "verifyingContract": usdc.address,
        }

        types = {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "Permit": [
                {"name": "owner", "type": "address"},
                {"name": "spender", "type": "address"},
                {"name": "value", "type": "uint256"},
                {"name": "nonce", "type": "uint256"},
                {"name": "deadline", "type": "uint256"},
            ],
        }

        message = {
            "owner": wallet.address,
            "spender": spender.address,
            "value": amount,
            "nonce": nonce,
            "deadline": deadline,
        }

        # Encode and sign the permit data
        typed_data = {
            "types": types,
            "domain": domain,
            "primaryType": "Permit",
            "message": message,
        }

        signature = Account.sign_message(
            encode_typed_data(full_message=typed_data), wallet.private_key
        )

        calldata = usdc.permit.encode_input(
            wallet.address,
            spender.address,
            self.approval_amount,
            deadline,
            signature.v,
            signature.r,
            signature.s,
        )

        return calldata

    def relayCalls(self, multicall_data):
        tx = multicall.aggregate(multicall_data, {"from": self.insurer})
        tx.wait(1)

    # Send batched permits via multicall
    def batch_process(self, num_wallets=1, get_call_data=lambda x: None):
        multicall_data = []
        if self.farmer_hd_last_index is not None:
            self.farmer_hd_start_index = self.farmer_hd_last_index + 1
        else:
            self.farmer_hd_last_index = self.farmer_hd_start_index
        last_index = self.farmer_hd_start_index
        try:
            for w_idx in range(
                self.farmer_hd_start_index,
                min(
                    self.farmer_hd_start_index + num_wallets,
                    self.farmer_hd_max_index + 1,
                ),
            ):
                self.farmer_hd_last_index = w_idx

                multicall_data.extend(get_call_data(w_idx))

                # Break into batches
                if len(multicall_data) >= self.batch_size:
                    print(
                        (
                            f"Sending batch of {len(multicall_data)} permits "
                            f"(starting from {last_index} to {w_idx})"
                        )
                    )
                    last_index = w_idx
                    self.relayCalls(multicall_data)
                    multicall_data = []  # Reset batch

                self.farmer_hd_last_index = w_idx

            # Send remaining transactions
            if len(multicall_data) > 0:
                print(
                    (
                        f"Sending batch of {len(multicall_data)} permits "
                        f"(starting from {self.farmer_hd_last_index} to {w_idx})"
                    )
                )
                self.relayCalls(multicall_data)

        except Exception as e:
            print(f"Error: {e}")

    def get_multi_permit_calldata(self, index):
        wallet = getHdWallet(context.farmer_hd_base, index)
        multicall_data = []
        nonce = usdc.nonces(wallet.address)  # Get current nonce
        for s_idx, spender in enumerate(self.token_spenders):
            deadline = int(time()) + 3600  # 1 hour from now

            # Encode permit call
            permit_calldata = self.get_permit_calldata(
                wallet, spender, self.approval_amount, nonce + s_idx, deadline
            )

            multicall_data.append((usdc.address, permit_calldata))
        return multicall_data

    def get_airdrop_calldata(self, index):
        wallet = getHdWallet(context.farmer_hd_base, index)
        multicall_data = []
        for partner, funding in self.funding["single"]["USDC"].items():
            calldata = usdc.transferFrom.encode_input(
                self.partnerWallets[partner]["wallet"].address, wallet.address, funding
            )
            multicall_data.append((usdc.address, calldata))
        return multicall_data

    def batch_permits(self, num_wallets=1):
        self.batch_process(num_wallets, self.get_multi_permit_calldata)

    def batch_airdrop(self, num_wallets=1):
        self.batch_process(num_wallets, self.get_airdrop_calldata)

    def check_allowance(self, start, stop, verbose=False):
        if verbose:
            print(
                (f"{'Allowances:'.ljust(40)}" f"{' '.join(self.token_spender_names)}")
            )
        for i in range(start, stop):

            wallet = getHdWallet(context.farmer_hd_base, i)
            values = [
                usdc.allowance(wallet.address, spender.address)
                for spender in self.token_spenders
            ]
            allowances = " ".join([str(value).ljust(20) for value in values])
            if verbose:
                print(f"Allowance for wallet {wallet.address} ({i}):  {allowances}")
            else:
                if i % 100 == 0:
                    print(f"Checking wallet {i}-{i+100}...")
                if any(value != self.approval_amount for value in values):
                    print(f"Allowance for wallet {wallet.address} ({i}):  {allowances}")

    def check_balances(self, start, stop, verbose=False):
        for i in range(start, stop):
            wallet = getHdWallet(context.farmer_hd_base, i)
            bal = usdc.balanceOf(wallet.address)
            if verbose:
                print(f"Balance for wallet {wallet.address} ({i}):  {bal}")
            else:
                if i % 100 == 0:
                    print(f"Checking wallet {i}-{i+100}...")
                if bal != self.funding["total"]["farmer"]["USDC"]:
                    print(f"Balance for wallet {wallet.address} ({i}):  {bal}")


farmer_funding = FarmerFunding()
