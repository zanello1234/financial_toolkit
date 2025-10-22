# 📋 Installation & Configuration Guide

## 🔧 System Requirements

### Minimum Requirements
- **Odoo Version**: 18.0 or higher
- **Python Version**: 3.8+
- **Database**: PostgreSQL 12+
- **Memory**: 2GB RAM minimum
- **Storage**: 100MB available space

### Required Modules
- `account` - Accounting (Core Odoo)
- `sale` - Sales Management (Core Odoo)
- `purchase` - Purchase Management (Core Odoo)

## 🚀 Installation Steps

### Method 1: Odoo Apps Store (Recommended)
1. Go to **Apps** menu in your Odoo instance
2. Search for "Credit Card Management Pro"
3. Click **Install**
4. Wait for installation to complete
5. Refresh your browser

### Method 2: Manual Installation
1. Download the module package
2. Extract to your Odoo addons directory
3. Update apps list: `python odoo-bin -u all -d your_database`
4. Install via Apps menu

## ⚙️ Initial Configuration

### Step 1: Enable Developer Mode
1. Go to **Settings** → **General Settings**
2. Scroll to **Developer Tools**
3. Enable **Developer Mode**

### Step 2: Configure Credit Card Plans
1. Navigate to **Accounting** → **Configuration** → **Credit Card Plans**
2. Create your first card plan:
   - **Name**: e.g., "Visa - Bank ABC"
   - **Commission**: Set the percentage (e.g., 2.5%)
   - **Accreditation Days**: Days for settlement (e.g., 2)
   - **Account**: Select the corresponding bank account

### Step 3: Configure Payment Methods
1. Go to **Accounting** → **Configuration** → **Payment Methods**
2. Create/edit payment methods for each card type
3. Link each method to the corresponding card plan

### Step 4: Set Up Fee Management
1. Create vendor for card processor fees:
   - **Accounting** → **Vendors** → **Create**
   - Set vendor name (e.g., "Visa Processing Fees")
2. Configure expense account for fees:
   - **Accounting** → **Configuration** → **Chart of Accounts**
   - Create account "Credit Card Fees" (expense type)

## 🎯 Quick Start Workflow

### Processing Your First Payment
1. **Create Sales Order** with credit card payment
2. **Confirm Order** - surcharge automatically calculated
3. **Register Payment** using configured card method
4. **Create Accreditation** - automatically generated
5. **Process Batch Transfer** when ready
6. **Invoice Fees** using the fee wizard

## 🔐 User Permissions

### Accounting Manager
- Full access to all features
- Can configure card plans
- Can process batch transfers
- Can generate fee invoices

### Accounting User
- Can create accreditations
- Can view batch transfers
- Can process payments
- Limited configuration access

### Sales User
- Can create sales orders with credit card payments
- Can view payment status
- Read-only access to credit card data

## 🛠️ Advanced Configuration

### Multi-Company Setup
1. Configure card plans per company
2. Set up inter-company accounts if needed
3. Configure company-specific payment methods

### Multi-Currency Support
1. Enable multi-currency in Accounting settings
2. Configure exchange rates
3. Set up currency-specific card plans

### Holiday Calendar Integration
1. Go to **Settings** → **Technical** → **Resource Calendar**
2. Configure business days for accurate accreditation dates

## 📊 Reporting Setup

### Default Reports Available
- Credit Card Summary
- Fee Analysis
- Reconciliation Status
- Cash Flow Predictions

### Custom Reports
- Use Odoo Studio for custom views
- Export data for external analysis
- Set up automated report generation

## 🔄 Data Migration

### From Previous Versions
1. Backup your database
2. Test migration in staging environment
3. Run data migration scripts if provided
4. Verify data integrity

### From Other Systems
1. Export data in CSV format
2. Use Odoo import tools
3. Map fields correctly
4. Validate imported data

## 🆘 Troubleshooting

### Common Issues

**Installation fails**
- Check Odoo version compatibility
- Verify all dependencies are installed
- Check server logs for errors

**Surcharges not calculating**
- Verify payment method configuration
- Check card plan settings
- Ensure sale order has correct payment terms

**Reconciliation not working**
- Check bank account configuration
- Verify payment journal settings
- Ensure batch transfer is confirmed

### Getting Help
- **Email Support**: support@onlyone.odoo.com
- **Website**: www.onlyone.odoo.com
- **Documentation**: Check module README
- **Community**: Odoo Community Forums

## 🔄 Regular Maintenance

### Weekly Tasks
- Review pending reconciliations
- Process fee invoices
- Check batch transfer status

### Monthly Tasks
- Reconcile card processor statements
- Review fee accuracy
- Update card plan rates if needed

### Quarterly Tasks
- Review user permissions
- Update system documentation
- Check for module updates

---

**Need Help?** Contact our support team at support@onlyone.odoo.com