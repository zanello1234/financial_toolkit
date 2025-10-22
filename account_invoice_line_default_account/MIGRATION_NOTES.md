# Account Invoice Line Default Account - V18 Migration

## Overview

This module has been successfully migrated from Odoo V16 to V18. It provides default income and expense accounts for partners, similar to how products have default accounts.

## Key Changes in V18 Migration

### 1. Dependencies
- **Removed**: `base_partition` dependency (not available in V18)
- **Updated**: Version from 16.0.1.0.0 to 18.0.1.0.0

### 2. Code Updates
- Replaced `odoo.fields.first()` with native Python list indexing `[0]`
- Updated domain syntax from lambda functions to string format
- Replaced `.partition()` method with native Python set iteration
- Maintained all core functionality while ensuring V18 compatibility

### 3. Models Updated
- `account.move.line`: Updated computation and write methods
- `res.partner`: Updated field domains for V18 compatibility

### 4. Tests
- Updated all test files to work with V18
- Removed deprecated `first()` utility function usage
- Maintained test coverage for all features

## Compatibility
- **Odoo Version**: 18.0
- **Python**: 3.8+
- **Dependencies**: account (core module)

## Installation Notes
- No data migration required from V16
- Fields and functionality remain identical from user perspective
- All existing configurations will work without changes