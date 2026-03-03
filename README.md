# Monarch for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration) [![Release badge](https://img.shields.io/github/v/release/sanghviharshit/ha-monarchmoney?style=for-the-badge)](https://github.com/sanghviharshit/ha-monarchmoney/releases/latest) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

**Integration for [Monarch Money](https://www.monarchmoney.com/referral/craudhiyod) in [Home Assistant](https://www.home-assistant.io/)**

Track all your Monarch Money financial data — account balances, net worth, cash flow, investments, and more — directly in Home Assistant.

## Features

- **Account sensors** — balances grouped by type (Cash, Credit Cards, Investments, Loans, Real Estate, Vehicles, Valuables, etc.)
- **Net Worth sensor** — total net worth with assets/liabilities breakdown
- **Cash Flow sensor** — monthly savings, income, and expenses with savings rate
- **Income & Expense sensors** — totals with per-category breakdowns
- **Credit Score sensors** *(optional)* — per household member, with score history and change tracking
- **Investment Holdings sensors** *(optional)* — individual securities with price, quantity, cost basis, and gain/loss
- **Recurring Transactions calendar** *(optional)* — upcoming bills and subscriptions as calendar events
- **Refresh button** — manually trigger a data refresh
- **MFA support** — manual code entry or automatic TOTP via secret key

## Installation

### HACS (Recommended)

1. In HACS, go to **Integrations** and click **+**.
2. Search for **Monarch** and install.
3. Restart Home Assistant.

### Manual

1. Copy the `custom_components/monarchmoney` folder to your Home Assistant `custom_components` directory.
2. Restart Home Assistant.

## Setup

1. Go to **Settings > Devices & Services > Add Integration**.
2. Search for **Monarch** and follow the prompts.
3. Log in with your Monarch Money email and password. If MFA is enabled, you'll be prompted for your code (or provide your TOTP secret for automatic MFA).

## Configuration

After setup, go to the integration's **Options** to configure:

| Option | Default | Description |
|---|---|---|
| Scan interval | 3600s (1hr) | How often to poll Monarch's API |
| Timeout | 30s | API request timeout |
| Credit score | Off | Enable credit score sensors |
| Investment holdings | Off | Enable per-security holding sensors |
| Recurring transactions | Off | Enable recurring transactions calendar |

## Planned

- [ ] Add screenshot with masked numbers
- [ ] Optional sensors for recent transactions (configurable count)

## Credits

- [monarchmoneycommunity](https://github.com/bradleyseanf/monarchmoneycommunity) (Forked from [monarchmoney](https://github.com/hammem/monarchmoney))
