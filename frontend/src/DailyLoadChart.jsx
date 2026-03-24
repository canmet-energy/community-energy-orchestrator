/* eslint-disable react/prop-types */
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { formatPower } from './units';

function DailyEnergyChart({ dailyLoadData, analysisData }) {
    if (!dailyLoadData || !dailyLoadData.data) {
        return <div>Loading daily energy data...</div>;
    }

    const chartData = dailyLoadData.data;

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
                        Average: {data.avg_energy.toFixed(3)} GJ
                    </p>
                    <p className="value" style={{ color: 'var(--chart-line-peak)' }}>
                        Peak: {data.peak_energy.toFixed(3)} GJ
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
    const highestAvg = Math.max(...chartData.map(d => d.avg_energy));
    const avgDay = chartData.find(d => d.avg_energy === highestAvg)?.day || 1;

    // Get peak hourly energy from analysis data
    const peakHourlyKw = analysisData?.heating_energy?.max_hourly_kw || 0;
    const peakHourlyTime = analysisData?.heating_energy?.max_hourly_time || '';

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
        <div className="daily-load-chart">
            <h3>Daily Heating Energy Profile</h3>
            <p className="chart-description">
                This chart shows the daily average and peak heating energy throughout the year. 
                Each point represents one day (average of 24 hourly readings).
            </p>
            
            <div className="chart-container">
                <ResponsiveContainer width="100%" height={400}>
                    <LineChart
                        data={chartData}
                        margin={{ top: 5, right: 30, left: 20, bottom: 30 }}
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
                            label={{ 
                                value: 'Heating Energy (GJ)', 
                                angle: -90, 
                                position: 'insideLeft',
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
                            xAxisId="boundary"
                            type="monotone" 
                            dataKey="avg_energy" 
                            stroke="var(--chart-line-average)" 
                            name="Average Energy"
                            dot={false}
                            strokeWidth={2}
                        />
                        <Line 
                            xAxisId="boundary"
                            type="monotone" 
                            dataKey="peak_energy" 
                            stroke="var(--chart-line-peak)" 
                            name="Peak Energy"
                            dot={false}
                            strokeWidth={2}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>

            {/* Summary Statistics */}
            <div className="load-stats">
                <h4>Summary Statistics</h4>
                <div className="stat-cards">
                    <div className="stat-card">
                        <div className="stat-label">Peak Hourly Energy</div>
                        <div className="stat-value">{formatPower(peakHourlyKw)}</div>
                        {peakHourlyTime && (
                            <div className="stat-meta">on {formatTimestamp(peakHourlyTime)}</div>
                        )}
                    </div>
                    <div className="stat-card">
                        <div className="stat-label">Highest Average Hourly Energy</div>
                        <div className="stat-value">{highestAvg.toFixed(3)} GJ</div>
                        <div className="stat-meta">on {dayToMonthDay(avgDay)}</div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default DailyEnergyChart;
