/**
 * Energy unit conversion utilities for frontend.
 * 
 * Provides utilities for converting energy values in Joules
 * to human-readable formats with appropriate units (J, kJ, MJ, GJ, TJ).
 * The goal is to keep displayed numbers with 3 or fewer digits before
 * the decimal point for better readability.
 */

/**
 * Convert energy value in GJ to the most appropriate unit.
 * Ensures the resulting number has 3 or fewer digits before the decimal point.
 * 
 * @param {number} valueGJ - Energy value in gigajoules (GJ)
 * @returns {{value: number, unit: string}} Object with converted value and unit
 * 
 * @example
 * convertEnergyToReadable(0.0005) // { value: 500.0, unit: 'kJ' }
 * convertEnergyToReadable(0.5)    // { value: 500.0, unit: 'MJ' }
 * convertEnergyToReadable(50.0)   // { value: 50.0, unit: 'GJ' }
 * convertEnergyToReadable(1234.0) // { value: 1.234, unit: 'TJ' }
 */
export function convertEnergyToReadable(valueGJ) {
    // Convert GJ to J for base calculation
    const valueJ = valueGJ * 1e9;
    
    // Define unit thresholds (in Joules)
    const TJ = 1e12;  // 1 TJ = 1,000 GJ
    const GJ = 1e9;   // 1 GJ = 1,000 MJ
    const MJ = 1e6;   // 1 MJ = 1,000 kJ
    const kJ = 1e3;   // 1 kJ = 1,000 J
    
    // Select appropriate unit (keep number <= 999.999...)
    if (Math.abs(valueJ) >= TJ) {
        return { value: valueJ / TJ, unit: 'TJ' };
    } else if (Math.abs(valueJ) >= GJ) {
        return { value: valueJ / GJ, unit: 'GJ' };
    } else if (Math.abs(valueJ) >= MJ) {
        return { value: valueJ / MJ, unit: 'MJ' };
    } else if (Math.abs(valueJ) >= kJ) {
        return { value: valueJ / kJ, unit: 'kJ' };
    } else {
        return { value: valueJ, unit: 'J' };
    }
}

/**
 * Format energy value with appropriate unit for display.
 * 
 * @param {number} valueGJ - Energy value in gigajoules (GJ)
 * @param {number} decimalPlaces - Number of decimal places to show (default: 3)
 * @returns {string} Formatted string like "123.456 GJ" or "1.234 TJ"
 * 
 * @example
 * formatEnergy(1234.567)      // "1.235 TJ"
 * formatEnergy(50.123)        // "50.123 GJ"
 * formatEnergy(50.123, 1)     // "50.1 GJ"
 */
export function formatEnergy(valueGJ, decimalPlaces = 3) {
    const { value, unit } = convertEnergyToReadable(valueGJ);
    return `${value.toFixed(decimalPlaces)} ${unit}`;
}

/**
 * Format energy value with thousands separator and appropriate unit.
 * 
 * @param {number} valueGJ - Energy value in gigajoules (GJ)
 * @param {number} decimalPlaces - Number of decimal places to show (default: 1)
 * @returns {string} Formatted string like "1,234.5 GJ" or "1.2 TJ"
 * 
 * @example
 * formatEnergyWithThousandsSep(1234.567) // "1.2 TJ"
 * formatEnergyWithThousandsSep(50.123)   // "50.1 GJ"
 */
export function formatEnergyWithThousandsSep(valueGJ, decimalPlaces = 1) {
    const { value, unit } = convertEnergyToReadable(valueGJ);
    
    // Only add thousands separator if the integer part is >= 1000
    let formattedValue;
    if (Math.abs(value) >= 1000) {
        formattedValue = value.toLocaleString(undefined, {
            minimumFractionDigits: decimalPlaces,
            maximumFractionDigits: decimalPlaces
        });
    } else {
        formattedValue = value.toFixed(decimalPlaces);
    }
    
    return `${formattedValue} ${unit}`;
}

/**
 * Get just the unit label for a given GJ value.
 * Useful for axis labels and headings.
 * 
 * @param {number} valueGJ - Energy value in gigajoules (GJ)
 * @returns {string} Unit string like "GJ" or "TJ"
 */
export function getEnergyUnit(valueGJ) {
    const { unit } = convertEnergyToReadable(valueGJ);
    return unit;
}

/**
 * Determine the best unit for an array of GJ values.
 * Useful for consistent axis labeling across multiple data points.
 * 
 * @param {number[]} valuesGJ - Array of energy values in GJ
 * @returns {string} Unit string to use for all values
 */
export function getBestUnitForRange(valuesGJ) {
    if (!valuesGJ || valuesGJ.length === 0) return 'GJ';
    
    // Use the maximum value to determine unit
    const maxValue = Math.max(...valuesGJ.map(Math.abs));
    return getEnergyUnit(maxValue);
}

/**
 * Convert a GJ value to a specific unit.
 * 
 * @param {number} valueGJ - Energy value in GJ
 * @param {string} targetUnit - Target unit ('J', 'kJ', 'MJ', 'GJ', 'TJ')
 * @returns {number} Converted value
 */
export function convertToUnit(valueGJ, targetUnit) {
    const valueJ = valueGJ * 1e9;
    
    switch (targetUnit) {
        case 'TJ':
            return valueJ / 1e12;
        case 'GJ':
            return valueJ / 1e9;
        case 'MJ':
            return valueJ / 1e6;
        case 'kJ':
            return valueJ / 1e3;
        case 'J':
            return valueJ;
        default:
            throw new Error(`Unknown unit: ${targetUnit}`);
    }
}
