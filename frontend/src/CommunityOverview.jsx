/* eslint-disable react/prop-types */

/**
 * Formats a housing type key like "pre-2000-single" into a readable label.
 * e.g. "pre-2000-single" → "Pre-2000 Single"
 */
function formatHousingType(key) {
    return key
        .split('-')
        .map((part) => {
            // Keep numeric parts (years) as-is
            if (/^\d+$/.test(part)) return part;
            // Capitalize first letter
            return part.charAt(0).toUpperCase() + part.slice(1);
        })
        .join(' ')
        // Rejoin year ranges: "Pre 2000" → "Pre-2000", "2001 2015" → "2001-2015"
        .replace(/(\d+)\s+(\d+)/g, '$1-$2')
        .replace(/(Pre|Post)\s+(\d+)/g, '$1-$2')
        // Clean up type labels
        .replace(/Row Mid/g, 'Row (Mid)')
        .replace(/Row End/g, 'Row (End)');
}

function CommunityOverview({ communityInfo }) {
    if (!communityInfo) return null;

    const {
        province_territory,
        population,
        hdd,
        weather_location,
        total_houses,
        housing_distribution,
    } = communityInfo;

    // Filter to only non-zero housing types
    const nonZeroHousing = housing_distribution
        ? Object.entries(housing_distribution).filter(([, count]) => count > 0)
        : [];

    return (
        <div className="community-overview">
            <h3>Community Overview</h3>
            <div className="overview-grid">
                <div className="overview-item">
                    <span className="overview-label">Province / Territory</span>
                    <span className="overview-value">{province_territory || 'N/A'}</span>
                </div>
                <div className="overview-item">
                    <span className="overview-label">Population</span>
                    <span className="overview-value">
                        {population != null ? population.toLocaleString() : 'N/A'}
                    </span>
                </div>
                <div className="overview-item">
                    <span className="overview-label">Heating Degree Days</span>
                    <span className="overview-value">
                        {hdd != null ? hdd.toLocaleString() : 'N/A'}
                    </span>
                </div>
                <div className="overview-item">
                    <span className="overview-label">Weather Station</span>
                    <span className="overview-value">{weather_location || 'N/A'}</span>
                </div>
                <div className="overview-item">
                    <span className="overview-label">Total Homes</span>
                    <span className="overview-value">
                        {total_houses != null ? total_houses.toLocaleString() : 'N/A'}
                    </span>
                </div>
            </div>

            {nonZeroHousing.length > 0 && (
                <div className="housing-distribution">
                    <h4>Housing Distribution</h4>
                    <div className="housing-tags">
                        {nonZeroHousing.map(([type, count]) => (
                            <span key={type} className="housing-tag">
                                {count} {formatHousingType(type)}
                            </span>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

export default CommunityOverview;
