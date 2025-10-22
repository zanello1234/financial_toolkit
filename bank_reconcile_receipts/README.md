# Bank Reconciliation Receipts & Payments

## Overview
This module extends Odoo's bank reconciliation functionality to automatically create customer receipts and vendor payments directly from reconciliation models.

## Features

### New Counterpart Types
- **Customer Receipts**: Automatically creates customer payment receipts
- **Vendor Payments**: Automatically creates vendor payment entries

### Configuration Options
- **Payment Method**: Choose specific payment method for created payments
- **Auto-post Payment**: Automatically post payments when created
- **Payment Memo Template**: Customize payment descriptions with variables

### Available Variables for Memo Template
- `{statement_name}`: Name of the bank statement
- `{partner_name}`: Partner name
- `{amount}`: Payment amount

## Usage

### Setup
1. Go to **Accounting > Configuration > Bank Reconciliation Models**
2. Create a new reconcile model or edit an existing one
3. Set **Counterpart Type** to either:
   - **Customer Receipts**: For payments received from customers
   - **Vendor Payments**: For payments made to suppliers
4. Configure payment settings:
   - Select appropriate **Payment Method**
   - Enable/disable **Auto-post Payment**
   - Customize **Payment Memo Template**

### Bank Reconciliation
1. Open bank reconciliation
2. Apply the configured reconcile model to statement lines
3. The system will automatically:
   - Create the appropriate payment record
   - Post the payment (if auto-post is enabled)
   - Attempt to reconcile with the bank statement line

### Example Scenarios

#### Customer Receipt
- Bank statement shows: "Transfer from John Doe - $1,500"
- Apply "Customer Receipts" reconcile model
- Result: Customer receipt created for John Doe, $1,500

#### Vendor Payment
- Bank statement shows: "Payment to ABC Supplies - $850"
- Apply "Vendor Payments" reconcile model  
- Result: Vendor payment created for ABC Supplies, $850

## Technical Details

### Model Extensions
- Extends `account.reconcile.model` with new counterpart types
- Hooks into bank reconciliation process
- Creates `account.payment` records automatically

### Reconciliation Flow
1. Standard reconciliation rules apply first
2. Custom payment creation logic executes
3. Payments are created with proper configuration
4. Automatic reconciliation attempts occur

### Error Handling
- Payment creation errors don't break reconciliation
- Detailed logging for troubleshooting
- Graceful fallbacks for missing configuration

## Requirements
- Odoo 18.0+
- `account` module
- `account_accountant` module

## Installation
1. Place module in addons directory
2. Update module list
3. Install "Bank Reconciliation Receipts & Payments"

## Support
For issues or feature requests, contact your system administrator.