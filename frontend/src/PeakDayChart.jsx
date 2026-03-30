/* eslint-disable react/prop-types */
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { convertPowerToReadable, convertToPowerUnit, getBestPowerUnitForRange } from './units';

const GJ_TO_KW = 277.778;

function PeakDayChart({ peakDayData, category = 'heating' }) {
    if (!peakDayData || !peakDayData.data) {
        return <div>Loading peak day data...</div>;
    }

    const categoryLabel = category === 'heating' ? 'Heating' : 'Total';

    const { peak_day, peak_hour, peak_value_gj, hourly_data } = peakDayData.data;

    // Convert energy (GJ/hour) to power (kW)
    const allValuesKW = hourly_data.map(d => d.energy_gj * GJ_TO_KW);
    const bestUnit = getBestPowerUnitForRange(allValuesKW);

    // Convert all data to the best power unit
    const chartData = hourly_data.map(d => ({
        hour: d.hour,
        power: convertToPowerUnit(d.energy_gj * GJ_TO_KW, bestUnit),
        original_gj: d.energy_gj,
        original_kw: d.energy_gj * GJ_TO_KW
    }));

    // Helper function to convert day number to "Month Day" format
    const dayToMonthDay = (dayNum) => {
        // Month boundaries using actual calendar days
        const months = [
            { name: 'Jan', days: 31 },
            { name: 'Feb', days: 28 },
            { name: 'Mar', days: 31 },
            { name: 'Apr', days: 30 },
            { name: 'May', days: 31 },
            { name: 'Jun', days: 30 },
            { name: 'Jul', days: 31 },
            { name: 'Aug', days: 31 },
            { name: 'Sep', days: 30 },
            { name: 'Oct', days: 31 },
            { name: 'Nov', days: 30 },
            { name: 'Dec', days: 31 }
        ];

        const boundaries = [1];
        months.forEach(m => boundaries.push(boundaries[boundaries.length - 1] + m.days));

        for (let i = 0; i < months.length; i++) {
            if (dayNum >= boundaries[i] && dayNum < boundaries[i + 1]) {
                const dayOfMonth = dayNum - boundaries[i] + 1;
                return `${months[i].name} ${dayOfMonth}`;
            }
        }
        return `Day ${dayNum}`;
    };

    // Format hour number (0-23) to readable time
    const formatHour = (h) => {
        const period = h < 12 ? 'AM' : 'PM';
        const display = h === 0 ? 12 : h > 12 ? h - 12 : h;
        return `${display}:00 ${period}`;
    };

    // Custom tooltip
    const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
            const data = payload[0].payload;
            const { value: displayValue, unit } = convertPowerToReadable(data.original_kw);
            return (
                <div className="custom-tooltip">
                    <p className="label"><strong>{formatHour(data.hour)}</strong></p>
                    <p className="value" style={{ color: 'var(--chart-line-energy)' }}>
                        Power: {displayValue.toFixed(1)} {unit}
                    </p>
                </div>
            );
        }
        return null;
    };

    // Format peak value in power units
    const { value: peakDisplayValue, unit: peakUnit } = convertPowerToReadable(peak_value_gj * GJ_TO_KW);

    return (
        <div className="peak-day-chart">
            <h3>Peak Day Hourly {categoryLabel} Power Profile</h3>
            <p className="chart-description">
                This chart shows the hourly {categoryLabel.toLowerCase()} power profile for {dayToMonthDay(peak_day)}, 
                the day with the highest single-hour power demand of the year.
            </p>
            
            <div className="chart-container">
                <ResponsiveContainer width="100%" height={400}>
                    <LineChart
                        data={chartData}
                        margin={{ top: 5, right: 30, left: 20, bottom: 30 }}
                    >
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis 
                            dataKey="hour" 
                            domain={[0, 24]}
                            ticks={[0, 4, 8, 12, 16, 20, 24]}
                            tickFormatter={(h) => {
                                if (h === 0 || h === 24) return '12 AM';
                                if (h < 12) return `${h} AM`;
                                if (h === 12) return '12 PM';
                                return `${h - 12} PM`;
                            }}
                            dy={6}
                            label={{ value: 'Hour of Day', position: 'insideBottom', offset: -25 }}
                        />
                        <YAxis 
                            label={{ 
                                value: `${categoryLabel} Power (${bestUnit})`, 
                                angle: -90, 
                                position: 'insideLeft',
                                dx: -10,
                                style: { textAnchor: 'middle' }
                            }}
                        />
                        <Tooltip content={<CustomTooltip />} />
                        <Legend 
                            verticalAlign="top" 
                            align="right"
                            wrapperStyle={{ paddingBottom: '10px' }}
                        />
                        <Line 
                            type="monotone" 
                            dataKey="power" 
                            stroke="var(--chart-line-energy)" 
                            name="Hourly Power"
                            strokeWidth={2}
                            dot={{ r: 3 }}
                            activeDot={{ r: 5 }}
                        />
                    </LineChart>
                    </ResponsiveContainer>
            </div>

            {/* Summary Statistics */}
            <div className="peak-day-stats">
                <h4>Peak Day Summary</h4>
                <div className="stat-cards">
                    <div className="stat-card">
                        <div className="stat-label">Peak Day</div>
                        <div className="stat-value">{dayToMonthDay(peak_day)}</div>
                        <div className="stat-meta">Day {peak_day} of the year</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-label">Peak Hour</div>
                        <div className="stat-value">{formatHour(peak_hour)}</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-label">Peak Power Value</div>
                        <div className="stat-value">{peakDisplayValue.toFixed(1)} {peakUnit}</div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default PeakDayChart;
