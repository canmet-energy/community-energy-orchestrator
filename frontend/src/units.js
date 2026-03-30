/**
 * Unit scaling and formatting utilities.
 *
 * Uses a single generic scaler that works with any unit system (Joules,
 * Watt-hours, Watts, etc.). Each unit system is defined as a simple list
 * of { threshold, suffix } entries. To add a new unit system, just define
 * a new scale array and call the helpers.
 *
 * The scaler picks the largest unit where the value stays >= 1, keeping
 * displayed numbers compact (ideally ≤ 3 digits before the decimal).
 */

// ==================== Unit System Definitions ====================

/**
 * A unit scale definition.
 * Each entry is [divisor_from_base, suffix].
 * Must be ordered largest → smallest.
 * The input value is first converted to the base unit using `toBase`.
 */

const JOULE_SCALE = {
    toBase: 1e9, // input is GJ → multiply to get J
    tiers: [
        [1e12, 'TJ'],
        [1e9,  'GJ'],
        [1e6,  'MJ'],
        [1e3,  'kJ'],
        [1,    'J'],
    ],
    defaultUnit: 'GJ',
};

const WATT_HOUR_SCALE = {
    toBase: 1e3, // input is kWh → multiply to get Wh
    tiers: [
        [1e9,  'GWh'],
        [1e6,  'MWh'],
        [1e3,  'kWh'],
        [1,    'Wh'],
    ],
    defaultUnit: 'kWh',
};

const WATT_SCALE = {
    toBase: 1e3, // input is kW → multiply to get W
    tiers: [
        [1e9,  'GW'],
        [1e6,  'MW'],
        [1e3,  'kW'],
        [1,    'W'],
    ],
    defaultUnit: 'kW',
};

// ==================== Generic Helpers ====================

/**
 * Scale a value to the most human-readable unit in the given system.
 *
 * @param {number} inputValue - Value in the input unit (e.g. GJ, kWh, kW)
 * @param {object} scale - One of the *_SCALE definitions above
 * @returns {{value: number, unit: string}}
 */
function scaleValue(inputValue, scale) {
    const baseValue = inputValue * scale.toBase;
    for (const [divisor, suffix] of scale.tiers) {
        if (Math.abs(baseValue) >= divisor) {
            return { value: baseValue / divisor, unit: suffix };
        }
    }
    // Fallback: use the smallest tier
    const [divisor, suffix] = scale.tiers[scale.tiers.length - 1];
    return { value: baseValue / divisor, unit: suffix };
}

/**
 * Format a scaled value as a string.
 *
 * @param {number} inputValue - Value in the input unit
 * @param {object} scale - Unit scale definition
 * @param {number} decimalPlaces - Decimal places to show
 * @returns {string} e.g. "50.123 GJ"
 */
function formatScaled(inputValue, scale, decimalPlaces) {
    const { value, unit } = scaleValue(inputValue, scale);
    return `${value.toFixed(decimalPlaces)} ${unit}`;
}

/**
 * Format a scaled value with thousands separators.
 *
 * @param {number} inputValue - Value in the input unit
 * @param {object} scale - Unit scale definition
 * @param {number} decimalPlaces - Decimal places to show
 * @returns {string} e.g. "1,234.5 GJ"
 */
function formatScaledWithSep(inputValue, scale, decimalPlaces) {
    const { value, unit } = scaleValue(inputValue, scale);
    let formatted;
    if (Math.abs(value) >= 1000) {
        formatted = value.toLocaleString(undefined, {
            minimumFractionDigits: decimalPlaces,
            maximumFractionDigits: decimalPlaces,
        });
    } else {
        formatted = value.toFixed(decimalPlaces);
    }
    return `${formatted} ${unit}`;
}

/**
 * Convert an input value to a specific target unit within a scale.
 *
 * @param {number} inputValue - Value in the input unit
 * @param {string} targetUnit - Target unit suffix (e.g. 'MJ', 'kWh')
 * @param {object} scale - Unit scale definition
 * @returns {number} Converted value
 */
function convertScaledToUnit(inputValue, targetUnit, scale) {
    const baseValue = inputValue * scale.toBase;
    for (const [divisor, suffix] of scale.tiers) {
        if (suffix === targetUnit) {
            return baseValue / divisor;
        }
    }
    throw new Error(`Unknown unit: ${targetUnit}`);
}

// ==================== Joule (Energy in GJ) Exports ====================

export function convertEnergyToReadable(valueGJ) {
    return scaleValue(valueGJ, JOULE_SCALE);
}

export function formatEnergy(valueGJ, decimalPlaces = 1) {
    return formatScaled(valueGJ, JOULE_SCALE, decimalPlaces);
}

export function formatEnergyWithThousandsSep(valueGJ, decimalPlaces = 1) {
    return formatScaledWithSep(valueGJ, JOULE_SCALE, decimalPlaces);
}

export function getEnergyUnit(valueGJ) {
    return scaleValue(valueGJ, JOULE_SCALE).unit;
}

export function getBestUnitForRange(valuesGJ) {
    if (!valuesGJ || valuesGJ.length === 0) return JOULE_SCALE.defaultUnit;
    const maxValue = Math.max(...valuesGJ.map(Math.abs));
    return getEnergyUnit(maxValue);
}

export function convertToUnit(valueGJ, targetUnit) {
    return convertScaledToUnit(valueGJ, targetUnit, JOULE_SCALE);
}

// ==================== Watt-hour (Energy in kWh) Exports ====================

export function convertEnergyWhToReadable(valueKWh) {
    return scaleValue(valueKWh, WATT_HOUR_SCALE);
}

export function formatEnergyWh(valueKWh, decimalPlaces = 1) {
    return formatScaled(valueKWh, WATT_HOUR_SCALE, decimalPlaces);
}

export function formatEnergyWhWithThousandsSep(valueKWh, decimalPlaces = 1) {
    return formatScaledWithSep(valueKWh, WATT_HOUR_SCALE, decimalPlaces);
}

// ==================== Power (in kW) Exports ====================

export function convertPowerToReadable(valueKW) {
    return scaleValue(valueKW, WATT_SCALE);
}

export function formatPower(valueKW, decimalPlaces = 1) {
    return formatScaled(valueKW, WATT_SCALE, decimalPlaces);
}

export function formatPowerWithThousandsSep(valueKW, decimalPlaces = 1) {
    return formatScaledWithSep(valueKW, WATT_SCALE, decimalPlaces);
}

export function getPowerUnit(valueKW) {
    return scaleValue(valueKW, WATT_SCALE).unit;
}

export function getBestPowerUnitForRange(valuesKW) {
    if (!valuesKW || valuesKW.length === 0) return WATT_SCALE.defaultUnit;
    const maxValue = Math.max(...valuesKW.map(Math.abs));
    return getPowerUnit(maxValue);
}

export function convertToPowerUnit(valueKW, targetUnit) {
    return convertScaledToUnit(valueKW, targetUnit, WATT_SCALE);
}
