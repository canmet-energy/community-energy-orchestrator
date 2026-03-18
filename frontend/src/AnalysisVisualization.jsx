/* eslint-disable react/prop-types */
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { formatEnergy, formatEnergyWithThousandsSep } from './units';

const COLORS = {
    propane: '#10B981',
    oil: '#3B82F6',
    electricity: '#FBBF24',
    'natural gas': '#EF4444',
    wood: '#8B5CF6'
};

function AnalysisVisualization({ analysisData }) {
    if (!analysisData) {
        return <div>Loading analysis data...</div>;
    }

    const { heating_load, heating_energy } = analysisData;
    const { by_source } = heating_energy;

    // Prepare data for pie chart
    const pieData = [
        { name: 'Propane', value: by_source.propane_gj, percent: by_source.propane_percent },
        { name: 'Oil', value: by_source.oil_gj, percent: by_source.oil_percent },
        { name: 'Electricity', value: by_source.electricity_gj, percent: by_source.electricity_percent },
        { name: 'Natural Gas', value: by_source.natural_gas_gj ?? 0, percent: by_source.natural_gas_percent ?? 0 },
        { name: 'Wood', value: by_source.wood_gj ?? 0, percent: by_source.wood_percent ?? 0 }
    ].filter(item => item.value > 0); // Only show non-zero values

    // Custom tooltip for pie chart
    const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
            const data = payload[0].payload;
            return (
                <div className="custom-tooltip">
                    <p className="label"><strong>{data.name}</strong></p>
                    <p className="value">{formatEnergyWithThousandsSep(data.value)}</p>
                    <p className="percent">{data.percent.toFixed(1)}%</p>
                </div>
            );
        }
        return null;
    };

    return (
        <div className="analysis-visualization">
            <h3>Energy Analysis Results</h3>

            {/* Total Annual Energy and Peak Hour Energy Display */}
            <div className="total-metrics-grid">
                <div className="total-energy-display">
                    <h4>Total Annual Energy Use</h4>
                    <p className="total-value">{formatEnergyWithThousandsSep(heating_energy.total_annual_gj)}</p>
                </div>
                <div className="total-energy-display peak-energy">
                    <h4>Peak Hourly Energy</h4>
                    <p className="total-value">{formatEnergy(heating_energy.max_hourly_gj)}</p>
                </div>
            </div>

            {/* Pie Chart for Energy Sources */}
            <div className="chart-container">
                <h4>Heating Energy by Source</h4>
                <ResponsiveContainer width="100%" height={350}>
                    <PieChart>
                        <Pie
                            data={pieData}
                            cx="50%"
                            cy="50%"
                            labelLine={false}
                            label={({ name }) => name}
                            outerRadius={100}
                            fill="#8884d8"
                            dataKey="value"
                        >
                            {pieData.map((entry, index) => (
                                <Cell 
                                    key={`cell-${index}`} 
                                    fill={COLORS[entry.name.toLowerCase()]} 
                                />
                            ))}
                        </Pie>
                        <Tooltip content={<CustomTooltip />} />
                    </PieChart>
                </ResponsiveContainer>

                {/* Energy by Source Breakdown */}
                <div className="source-breakdown-inline">
                    <h4>Energy Distribution by Source</h4>
                    <div className="source-cards">
                        {pieData.map((source) => (
                            <div
                                key={source.name}
                                className="source-card"
                                style={{ borderLeftColor: COLORS[source.name.toLowerCase()] }}
                            >
                                <div className="source-name">{source.name}</div>
                                <div className="source-value">{formatEnergyWithThousandsSep(source.value)}</div>
                                <div className="source-percent">{source.percent.toFixed(1)}%</div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Statistics Grid */}
            <div className="stats-grid">
                <div className="stat-section">
                    <h4>Heating Load Statistics</h4>
                    <p className="stat-description">(What the houses need)</p>
                    <div className="stat-cards">
                        <div className="stat-card">
                            <div className="stat-label">Total Annual Load</div>
                            <div className="stat-value">{formatEnergyWithThousandsSep(heating_load.total_annual_gj)}</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-label">Peak Hourly Load</div>
                            <div className="stat-value">{formatEnergy(heating_load.max_hourly_gj)}</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-label">Average Hourly Load</div>
                            <div className="stat-value">{formatEnergy(heating_load.avg_hourly_gj)}</div>
                        </div>
                    </div>
                </div>

                <div className="stat-section">
                    <h4>Heating Energy Statistics</h4>
                    <p className="stat-description">(What the equipment uses)</p>
                    <div className="stat-cards">
                        <div className="stat-card">
                            <div className="stat-label">Total Annual Energy</div>
                            <div className="stat-value">{formatEnergyWithThousandsSep(heating_energy.total_annual_gj)}</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-label">Peak Hourly Energy</div>
                            <div className="stat-value">{formatEnergy(heating_energy.max_hourly_gj)}</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-label">Average Hourly Energy</div>
                            <div className="stat-value">{formatEnergy(heating_energy.avg_hourly_gj)}</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default AnalysisVisualization;
