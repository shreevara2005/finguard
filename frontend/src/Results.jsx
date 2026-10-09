import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

const COLORS = ['#4f8cff', '#ff6b6b', '#4caf82', '#ffb454', '#c084fc', '#22d3ee']

function currency(n) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n)
}

export default function Results({ result }) {
  if (!result) return null

  const debtNames = result.monthly_plan.length > 0
    ? result.monthly_plan[0].debts.map((d) => d.name)
    : []

  const chartData = result.monthly_plan.map((row) => {
    const point = { month: row.month, Savings: row.savings_balance }
    row.debts.forEach((d) => {
      point[d.name] = d.balance
    })
    return point
  })

  return (
    <div>
      <div className="card">
        <h2>
          Optimal plan <span className="badge">{result.algorithm_used}</span>
        </h2>
        <div className="stat-grid">
          <div className="stat">
            <div className="label">Total interest paid</div>
            <div className="value">{currency(result.total_interest_paid)}</div>
          </div>
          <div className="stat">
            <div className="label">Months to debt-free</div>
            <div className="value">{result.months_to_debt_free}</div>
          </div>
          <div className="stat">
            <div className="label">Final savings</div>
            <div className="value">{currency(result.final_savings)}</div>
          </div>
          <div className="stat">
            <div className="label">Feasible?</div>
            <div className="value" style={{ color: result.feasible ? 'var(--success)' : 'var(--danger)' }}>
              {result.feasible ? 'Yes' : 'No'}
            </div>
          </div>
        </div>

        <h2>Extra-cash allocation weights</h2>
        <div className="row">
          {Object.entries(result.allocation_weights).map(([name, weight]) => (
            <div className="stat" key={name}>
              <div className="label">{name}</div>
              <div className="value">{(weight * 100).toFixed(1)}%</div>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <h2>Balances over time</h2>
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={chartData}>
            <CartesianGrid stroke="#2a333d" strokeDasharray="3 3" />
            <XAxis dataKey="month" stroke="#9aa5b1" label={{ value: 'Month', position: 'insideBottom', offset: -5, fill: '#9aa5b1' }} />
            <YAxis stroke="#9aa5b1" />
            <Tooltip
              contentStyle={{ background: '#1a2129', border: '1px solid #2a333d', borderRadius: 8 }}
              formatter={(value) => currency(value)}
            />
            <Legend />
            {debtNames.map((name, i) => (
              <Line key={name} type="monotone" dataKey={name} stroke={COLORS[i % COLORS.length]} dot={false} strokeWidth={2} />
            ))}
            <Line type="monotone" dataKey="Savings" stroke="#4caf82" dot={false} strokeWidth={2} strokeDasharray="5 3" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="card">
        <h2>Month-by-month plan</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Month</th>
                {debtNames.map((name) => (
                  <th key={name}>{name} payment</th>
                ))}
                <th>Savings contribution</th>
                <th>Savings balance</th>
              </tr>
            </thead>
            <tbody>
              {result.monthly_plan.map((row) => (
                <tr key={row.month}>
                  <td>{row.month}</td>
                  {row.debts.map((d) => (
                    <td key={d.name}>{currency(d.payment)}</td>
                  ))}
                  <td>{currency(row.savings_contribution)}</td>
                  <td>{currency(row.savings_balance)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
