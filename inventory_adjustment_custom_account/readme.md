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

## Technical Details

### Models

- **StockQuant**: Extended to include a custom account field (`x_adjustment_account_id`)
- **StockMove**: Overrides the `_account_entry_move` method to use custom accounts for inventory adjustments

### Key Methods

#### _account_entry_move

This method intercepts the creation of accounting entries for inventory movements and applies the following logic:

1. First calls the standard method to get the default accounting entry values
2. Checks the context for custom account mappings (`custom_adjustment_accounts`)
3. Determines if the current move is related to an inventory adjustment
4. Identifies the correct journal entry line to modify (using balance to determine credit/debit lines)
5. Replaces the default account with the custom account and updates the description
6. Returns the modified accounting entry values

### Context Passing

The module uses Odoo's context to pass custom accounts from the inventory adjustment UI to the accounting entry creation process. The context includes:

```python
{
    'custom_adjustment_accounts': {
        quant_id: account_id,
        ...
    }
}
```

## Troubleshooting

### Logging

The module includes extensive logging for troubleshooting purposes. You can enable debug logging to view detailed information about:

- Account selection process
- Journal entry modifications
- Inventory movement processing

To enable detailed logging, set the logger `odoo.addons.inventory_adjustment_custom_account` to debug level.

### Common Issues

1. **Custom account not being applied**
   - Check that the account is properly selected in the adjustment line
   - Verify that the account has the correct account type (expense, expense_depreciation, expense_direct_cost, income, or income_other)
   - Ensure the account is active and belongs to the same company

2. **View errors after installation**
   - This module is adapted for Odoo 17.0 which uses a different approach to view attributes
   - If you experience view errors, check that your Odoo version is compatible with the module

## Credits

Developed by ZanelloDev for inventory adjustment account customization needs.

## License

This module is published under the GNU LGPL v3 license.