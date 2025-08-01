# Flagging System Implementation

This document describes the implementation of the enhanced flagging system that replaces the contribute queue system.

## Overview

The contribute queue system has been replaced with a comprehensive flagging system that allows users to report data issues directly from council pages, providing better user experience and more efficient moderation.

## Changes Made

### 1. Contribute System Removal

- **Navigation**: Removed "Contribute" link from main navigation bar
- **URLs**: Disabled all contribute-related URLs while preserving backend models
- **Redirect Page**: Created informative page explaining the new system at `/contribute/`

### 2. Enhanced Flagging System

- **Flag Buttons**: Added flag buttons to financial counters and data fields
- **Modal Interface**: Comprehensive flagging modal with issue types and descriptions
- **Context-Aware**: Different flagging options based on content type
- **Email Notifications**: Admins receive emails when content is flagged

### 3. Flagging Capabilities

The system now supports flagging:
- **Financial Counters**: Individual counter values and calculations
- **Council Data**: General financial data and characteristics
- **Page Issues**: General council page problems

### 4. Moderation Interface

- **Admin Panel**: Enhanced flagged content interface
- **Statistics**: Comprehensive statistics and filtering
- **Action Buttons**: Direct moderation actions from the interface

## Technical Implementation

### Frontend Components

1. **Flagging System JavaScript** (`static/js/flagging-system.js`)
   - Modal creation and management
   - Flag button generation
   - AJAX form submission
   - Notification system

2. **Template Integration**
   - Flag buttons in council detail pages
   - Authentication-aware flagging
   - Responsive design elements

### Backend Components

1. **Enhanced Flag Content View** (`views/moderation.py`)
   - Support for virtual content types (financial counters)
   - Context-aware flagging
   - Email notification system
   - Duplicate prevention

2. **Flagged Content Admin** 
   - Updated list view with new content types
   - Proper statistics calculation
   - Enhanced filtering and search

### Data Model

The existing `Flag` model has been extended to support:
- Virtual content types (financial counters)
- Enhanced context information
- Priority levels and detailed descriptions

## Usage

### For Users

1. **Flagging Financial Data**:
   - Visit any council page
   - Click the small flag icon next to counter values
   - Select issue type and provide description
   - Submit flag for moderation

2. **General Data Issues**:
   - Use "Flag Data Issue" button in council controls
   - Describe the problem in detail
   - Select appropriate priority level

### For Administrators

1. **Viewing Flags**:
   - Navigate to "Flagged Content" in admin menu
   - View comprehensive list with filtering options
   - See detailed flag information and context

2. **Taking Action**:
   - Review flagged content and user reports
   - Take appropriate moderation actions
   - Resolve or dismiss flags as needed

## Email Notifications

Administrators receive email notifications when content is flagged:
- Subject line indicates flag type and priority
- Email includes detailed flag information
- Direct link to moderation interface

## Testing

Run the test script to validate the implementation:

```bash
python test_flagging_system.py
```

The test verifies:
- Contribute system removal
- JavaScript loading
- Flag button presence
- Admin navigation functionality

## Migration Notes

- All existing data is preserved
- Contribute URLs redirect to info page
- Existing flagging functionality remains intact
- Enhanced with new content type support

## Future Enhancements

Potential improvements include:
- React-based moderation dashboard
- Advanced notification system
- Automated flag resolution
- Integration with data quality monitoring