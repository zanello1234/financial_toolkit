# -*- coding: utf-8 -*-
{
    'name': 'Inventory Adjustment Custom Account',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Allows select  ing a specific account for inventory adjustments.',
    'description': """
# Inventory Adjustment Custom Account

## Overview

This module extends Odoo's standard inventory adjustment functionality by allowing users to specify custom expense or income accounts on a per-adjustment basis. Instead of using the default valuation accounts configured on inventory locations, users can select specific accounts for each inventory adjustment.

## Features

- Add a custom account field to inventory adjustment lines
- Override the standard accounting behavior to use the selected custom account
- Maintain detailed accounting records with specific accounts for different types of adjustments
- Compatible with Odoo 17.0 (modified for the new view attribute system)

## Installation

1. Download the module to your Odoo addons directory
2. Update the apps list in Odoo
3. Install the "Inventory Adjustment Custom Account" module

## Configuration

1. Navigate to **Accounting > Configuration > Chart of Accounts**
2. Ensure you have appropriate expense and income accounts set up for different types of inventory adjustments

## Usage

1. Go to **Inventory > Operations > Inventory Adjustments**
2. Create a new inventory adjustment or update an existing one
3. For each product line, you can now select a custom adjustment account
4. The selected account will be used instead of the default valuation account when posting the inventory adjustment
    """,
    'author': 'OnlyOne Odoo Team',
    'website': 'www.onlyone.odoo.com',
    'depends': [
        'stock_account', # Dependencia clave para la valoración de inventario
    ],
    'data': [
        'views/stock_quant_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3', # O la licencia que prefieras/necesites

}
