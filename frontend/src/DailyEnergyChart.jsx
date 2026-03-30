/* eslint-disable react/prop-types */
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { convertToUnit, getBestUnitForRange, formatEnergy, formatPower, getBestPowerUnitForRange, convertToPowerUnit } from './units';

const GJ_TO_KW = 277.778;

function DailyEnergyChart({ dailyLoadData, analysisData, category = 'heating' }) {
    if (!dailyLoadData || !dailyLoadData.data) {
        return <div>Loading daily energy data...</div>;
    }

    const isHeating = category === 'heating';
    const categoryLabel = isHeating ? 'Heating' : 'Total';
    const energyKey = isHeating ? 'heating_energy' : 'total_energy';

    const rawData = dailyLoadData.data;

    // Round up to a clean tick value (e.g. 1.5, 2, 2.5, 3, 4, 5, 10, 15, 20, ...)
    const niceMax = (value) => {
        if (value <= 0) return 1;
        const magnitude = Math.pow(10, Math.floor(Math.log10(value)));
        const residual = value / magnitude;
        let nice;
        if (residual <= 1) nice = 1;
        else if (residual <= 1.5) nice = 1.5;
        else if (residual <= 2) nice = 2;
        else if (residual <= 2.5) nice = 2.5;
        else if (residual <= 3) nice = 3;
        else if (residual <= 4) nice = 4;
        else if (residual <= 5) nice = 5;
        else if (residual <= 7.5) nice = 7.5;
        else nice = 10;
        return nice * magnitude;
    };

    // Determine the best unit for the left Y-axis (energy) based on avg values
    const avgValues = rawData.map(d => d.avg_energy);
    const bestEnergyUnit = getBestUnitForRange(avgValues);

    // Determine the best unit for the right Y-axis (power) based on peak values converted to kW
    const peakValuesKW = rawData.map(d => d.peak_energy * GJ_TO_KW);
    const bestPowerUnit = getBestPowerUnitForRange(peakValuesKW);

    // Convert all data to their respective best units
    const chartData = rawData.map(d => ({
        day: d.day,
        avg_energy: convertToUnit(d.avg_energy, bestEnergyUnit),
        peak_power: convertToPowerUnit(d.peak_energy * GJ_TO_KW, bestPowerUnit),
        original_avg_gj: d.avg_energy,
        original_peak_gj: d.peak_energy
    }));

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

    // Build cumulative boundary positions (day numbers where each month starts)
    // boundaries[0]=1 (Jan start), boundaries[1]=32 (Feb start), ... boundaries[12]=366 (end)
    const boundaries = [1];
    months.forEach(m => boundaries.push(boundaries[boundaries.length - 1] + m.days));

    // Helper function to convert day number to "Month Day" format
    const dayToMonthDay = (dayNum) => {
        for (let i = 0; i < months.length; i++) {
            if (dayNum >= boundaries[i] && dayNum < boundaries[i + 1]) {
                const dayOfMonth = dayNum - boundaries[i] + 1;
                return `${months[i].name} ${dayOfMonth}`;
            }
        }
        return `Day ${dayNum}`;
    };

    // Custom tooltip
    const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
            const data = payload[0].payload;
            return (
                <div className="custom-tooltip">
                    <p className="label"><strong>{dayToMonthDay(data.day)}</strong></p>
                    <p className="value" style={{ color: 'var(--chart-line-average)' }}>
                        Average: {formatEnergy(data.original_avg_gj)}
                    </p>
                    <p className="value" style={{ color: 'var(--chart-line-peak)' }}>
                        Peak: {formatPower(data.original_peak_gj * GJ_TO_KW)}
                    </p>
                </div>
            );
        }
        return null;
    };

    // Center of each month for label placement
    const monthCenters = months.map((m, i) => ({
        day: Math.round((boundaries[i] + boundaries[i + 1]) / 2),
        name: m.name,
    }));

    // Find highest daily average energy
    const highestAvg = Math.max(...rawData.map(d => d.avg_energy));
    const avgDay = rawData.find(d => d.avg_energy === highestAvg)?.day || 1;

    // Get peak hourly energy from analysis data
    const peakHourlyEnergy = analysisData?.[energyKey]?.max_hourly_kw || 0;
    const peakHourlyTime = analysisData?.[energyKey]?.max_hourly_time || '';

    // Format timestamp to "Jan 16, 7:00 PM" format
    const formatTimestamp = (timestamp) => {
        if (!timestamp) return '';
        try {
            const date = new Date(timestamp);
            const month = date.toLocaleString('en-US', { month: 'short' });
            const day = date.getDate();
            const time = date.toLocaleString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
            return `${month} ${day}, ${time}`;
        } catch {
            return '';
        }
    };

    return (
        <div className="daily-energy-chart">
            <h3>Daily {categoryLabel} Energy Profile</h3>
            <p className="chart-description">
                This chart shows the daily average and peak {categoryLabel.toLowerCase()} energy throughout the year. 
                Each point represents one day (average of 24 hourly readings).
            </p>
            
            <div className="chart-container">
                <ResponsiveContainer width="100%" height={400}>
                    <LineChart
                        data={chartData}
                        margin={{ top: 5, right: 50, left: 20, bottom: 30 }}
                    >
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        {/* Tick marks at month boundaries */}
                        <XAxis
                            xAxisId="boundary"
                            dataKey="day"
                            ticks={boundaries}
                            domain={[1, 366]}
                            tickLine={{ stroke: 'var(--chart-axis)', size: 6 }}
                            tick={{ fontSize: 0 }}
                            axisLine={{ stroke: 'var(--chart-axis)' }}
                        />
                        {/* Month labels centered between boundaries */}
                        <XAxis
                            xAxisId="label"
                            dataKey="day"
                            ticks={monthCenters.map(m => m.day)}
                            tickFormatter={(day) => {
                                const found = monthCenters.find(m => m.day === day);
                                return found ? found.name : '';
                            }}
                            domain={[1, 366]}
                            tickLine={false}
                            axisLine={false}
                            dy={-25}
                            label={{ value: 'Month', position: 'insideBottom'}}
                        />
                        <YAxis 
                            yAxisId="left"
                            domain={[0, dataMax => niceMax(dataMax * 2)]}
                            allowDecimals={false}
                            label={{ 
                                value: `Average Energy (${bestEnergyUnit})`, 
                                angle: -90, 
                                position: 'insideLeft',
                                dx: -10,
                                style: { textAnchor: 'middle', fill: 'var(--chart-line-average)' }
                            }}
                            tick={{ fill: 'var(--chart-line-average)' }}
                        />
                        <YAxis 
                            yAxisId="right"
                            orientation="right"
                            domain={[0, dataMax => niceMax(dataMax * 1.2)]}
                            allowDecimals={false}
                            label={{ 
                                value: `Peak Power (${bestPowerUnit})`, 
                                angle: 90, 
                                position: 'insideRight',
                                dx: 10,
                                style: { textAnchor: 'middle', fill: 'var(--chart-line-peak)' }
                            }}
                            tick={{ fill: 'var(--chart-line-peak)' }}
                        />
                        <Tooltip content={<CustomTooltip />} />
                        <Legend 
                            verticalAlign="top" 
                            align="right"
                            wrapperStyle={{ paddingBottom: '10px' }}
                        />
                        <Line 
                            xAxisId="boundary"
                            yAxisId="left"
                            type="monotone" 
                            dataKey="avg_energy" 
                            stroke="var(--chart-line-average)" 
                            name="Average Energy"
                            dot={false}
                            strokeWidth={2}
                        />
                        <Line 
                            xAxisId="boundary"
                            yAxisId="right"
                            type="monotone" 
                            dataKey="peak_power" 
                            stroke="var(--chart-line-peak)" 
                            name="Peak Power"
                            dot={false}
                            strokeWidth={2}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>

            {/* Summary Statistics */}
            <div className="energy-stats">
                <h4>Summary Statistics</h4>
                <div className="stat-cards">
                    <div className="stat-card">
                        <div className="stat-label">Peak Hourly Energy</div>
                        <div className="stat-value">{formatPower(peakHourlyEnergy)}</div>
                        {peakHourlyTime && (
                            <div className="stat-meta">on {formatTimestamp(peakHourlyTime)}</div>
                        )}
                    </div>
                    <div className="stat-card">
                        <div className="stat-label">Highest Average Hourly Energy</div>
                        <div className="stat-value">{formatEnergy(highestAvg)}</div>
                        <div className="stat-meta">on {dayToMonthDay(avgDay)}</div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default DailyEnergyChart;
