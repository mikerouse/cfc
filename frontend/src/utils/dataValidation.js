/**
 * Data validation utilities for detecting unrealistic council finance values
 */

/**
 * Validate monetary field values and suggest corrections
 */
export const validateMonetaryValue = (fieldSlug, value, councilContext = {}) => {
  const numValue = parseFloat(value);
  if (isNaN(numValue) || numValue <= 0) {
    return { isValid: true }; // Let other validation handle empty/invalid numbers
  }

  // ALL FINANCIAL DATA IS NOW STORED IN POUNDS (post-migration)
  // Define realistic ranges for UK council financial data in pounds
  const fieldRanges = {
    // Income fields - typical ranges for UK councils in pounds
    'business-rates-income': { min: 5_000_000, max: 500_000_000, typical: { min: 20_000_000, max: 200_000_000 } },
    'council-tax-income': { min: 10_000_000, max: 800_000_000, typical: { min: 50_000_000, max: 400_000_000 } },
    'total-income': { min: 50_000_000, max: 2_000_000_000, typical: { min: 200_000_000, max: 1_000_000_000 } },
    'non-ring-fenced-government-grants-income': { min: 1_000_000, max: 300_000_000, typical: { min: 10_000_000, max: 150_000_000 } },
    
    // Expenditure fields - in pounds
    'total-expenditure': { min: 50_000_000, max: 2_000_000_000, typical: { min: 200_000_000, max: 1_000_000_000 } },
    'interest-paid': { min: 100_000, max: 50_000_000, typical: { min: 1_000_000, max: 20_000_000 } },
    'capital-expenditure': { min: 5_000_000, max: 500_000_000, typical: { min: 20_000_000, max: 200_000_000 } },
    
    // Balance sheet fields - in pounds
    'current-liabilities': { min: 10_000_000, max: 500_000_000, typical: { min: 30_000_000, max: 200_000_000 } },
    'long-term-liabilities': { min: 20_000_000, max: 1_000_000_000, typical: { min: 50_000_000, max: 400_000_000 } },
    'total-debt': { min: 20_000_000, max: 1_500_000_000, typical: { min: 100_000_000, max: 600_000_000 } },
    'usable-reserves': { min: 5_000_000, max: 300_000_000, typical: { min: 15_000_000, max: 100_000_000 } },
    'unusable-reserves': { min: 50_000_000, max: 2_000_000_000, typical: { min: 200_000_000, max: 800_000_000 } },
    
    // Other fields - in pounds
    'pension-liability': { min: 100_000_000, max: 3_000_000_000, typical: { min: 300_000_000, max: 1_500_000_000 } },
    'finance-leases-pfi-liabilities': { min: 1_000_000, max: 200_000_000, typical: { min: 5_000_000, max: 50_000_000 } }
  };

  const range = fieldRanges[fieldSlug];
  if (!range) {
    return { isValid: true }; // No specific validation for this field
  }

  // Check if value is outside typical range
  const isOutsideTypical = numValue < range.typical.min || numValue > range.typical.max;
  const isOutsideAbsolute = numValue < range.min || numValue > range.max;

  if (isOutsideAbsolute) {
    // Value is completely unrealistic
    let suggestedValue = null;
    let suggestion = '';
    
    // Common correction patterns
    if (numValue > range.max * 100) {
      // Likely entered in pounds instead of millions
      suggestedValue = numValue / 1000000;
      suggestion = 'Looks like you entered pounds instead of millions';
    } else if (numValue > range.max * 10) {
      // Likely missing decimal point
      const stringValue = numValue.toString();
      if (stringValue.length >= 3) {
        suggestedValue = parseFloat(stringValue.slice(0, -3) + '.' + stringValue.slice(-3));
        suggestion = 'Missing decimal point?';
      }
    } else if (numValue > range.max * 1000 && numValue % 1000 === 0) {
      // Likely entered thousands instead of millions
      suggestedValue = numValue / 1000;
      suggestion = 'You may have entered thousands instead of millions';
    }

    // Ensure suggested value is within reasonable bounds
    if (suggestedValue && (suggestedValue < range.min || suggestedValue > range.max)) {
      suggestedValue = null;
    }

    return {
      isValid: false,
      severity: 'error',
      message: `This value (£${(numValue * 1000000).toLocaleString('en-GB')}) seems unrealistic for ${getFieldDisplayName(fieldSlug)}. Most UK councils have ${getFieldDisplayName(fieldSlug).toLowerCase()} between £${(range.typical.min * 1000000).toLocaleString('en-GB')} and £${(range.typical.max * 1000000).toLocaleString('en-GB')}.`,
      suggestedValue,
      suggestion,
      range
    };
  } else if (isOutsideTypical) {
    // Value is unusual but possible
    return {
      isValid: false,
      severity: 'warning',
      message: `This value is higher than typical for ${getFieldDisplayName(fieldSlug)}. Most UK councils range from £${(range.typical.min * 1000000).toLocaleString('en-GB')} to £${(range.typical.max * 1000000).toLocaleString('en-GB')}. Please double-check this figure.`,
      suggestedValue: null,
      range
    };
  }

  return { isValid: true };
};

/**
 * Get human-readable field display name
 */
const getFieldDisplayName = (fieldSlug) => {
  const fieldNames = {
    'business-rates-income': 'Business Rates Income',
    'council-tax-income': 'Council Tax Income', 
    'total-income': 'Total Income',
    'non-ring-fenced-government-grants-income': 'Government Grants Income',
    'total-expenditure': 'Total Expenditure',
    'interest-paid': 'Interest Paid',
    'capital-expenditure': 'Capital Expenditure',
    'current-liabilities': 'Current Liabilities',
    'long-term-liabilities': 'Long-term Liabilities',
    'total-debt': 'Total Debt',
    'usable-reserves': 'Usable Reserves',
    'unusable-reserves': 'Unusable Reserves',
    'pension-liability': 'Pension Liability',
    'finance-leases-pfi-liabilities': 'Finance Leases & PFI Liabilities'
  };
  
  return fieldNames[fieldSlug] || fieldSlug.split('-').map(word => 
    word.charAt(0).toUpperCase() + word.slice(1)
  ).join(' ');
};

/**
 * Validate integer fields (like population)
 */
export const validateIntegerValue = (fieldSlug, value, councilContext = {}) => {
  const numValue = parseInt(value);
  if (isNaN(numValue) || numValue <= 0) {
    return { isValid: true }; // Let other validation handle empty/invalid numbers
  }

  if (fieldSlug === 'population') {
    // UK council population ranges
    const minPop = 50000;   // Smallest councils
    const maxPop = 1700000; // Largest councils (Birmingham)
    
    if (numValue < minPop || numValue > maxPop) {
      let suggestedValue = null;
      let suggestion = '';
      
      if (numValue < 1000) {
        // Likely entered in thousands
        suggestedValue = numValue * 1000;
        suggestion = 'Did you mean thousands?';
      }
      
      return {
        isValid: false,
        severity: 'error',
        message: `Population of ${numValue.toLocaleString()} seems unrealistic for a UK council. Most councils serve between 50,000 and 1,700,000 people.`,
        suggestedValue,
        suggestion
      };
    }
  }

  return { isValid: true };
};

/**
 * Main validation function that routes to appropriate validator
 */
export const validateFieldValue = (field, value, councilContext = {}) => {
  if (!value || value === '') {
    return { isValid: true };
  }

  const contentType = field.contentType || field.content_type;
  
  switch (contentType) {
    case 'monetary':
      return validateMonetaryValue(field.slug, value, councilContext);
    case 'integer':
      return validateIntegerValue(field.slug, value, councilContext);
    default:
      return { isValid: true };
  }
};