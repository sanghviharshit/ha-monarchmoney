# Monarch for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs) ![Release badge](https://img.shields.io/github/v/release/sanghviharshit/ha-monarchmoney?style=for-the-badge) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

**Integration for Monarch in Home Assistant**

[Monarch](https://milacares.com/) is modern way to manage your money and lets you track all of your account balances, transactions, and investments in one place.

[Home Assistant](https://www.home-assistant.io/) is an open source home automation package that puts local control and privacy first.
This integration leverages Monarch's API to collect the accounts' data in Home Assistant.

## Installation

### HACS Install

- Use HACS and add [ha-monarchmoney](https://github.com/sanghviharshit/ha-monarchmoney) as a custom repo.
- Go to HACS (Community). Select _Integrations_ and click the + to add a new integration repository. Search for `Monarch` to find this repository, select it and install.
- Restart Home Assistant after installation.

### Manual Install

- Copy the `monarchmoney` folder inside `custom_components` to your Home Assistant's `custom_components` folder.
- Restart Home Assistant after installation.

### Setup

After restarting go to _Configuration_, _Integrations_, click the + to add a new integration and find the Monarch integration to set up.

Log in with your Monarch account.

The integration will detect all accounts added to your Monarch account. You can override the name and entity ID in Home Assistant's entity settings.

## Credits

- [monarchmoney](https://github.com/hammem/monarchmoney) from [hammem](https://github.com/hammem)

## ToDo List

- Better exception handling
- config flow handler for options (timeout, scan interval, monitored categories)
- Maybe brokerage transactions
- Maybe investment holdings
