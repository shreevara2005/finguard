import { useState } from 'react'

let nextId = 1

function newDebt() {
  return { id: nextId++, name: '', balance: '', apr: '', min_payment: '' }
}

export default function PlanForm({ onSubmit, loading }) {
  const [monthlyCash, setMonthlyCash] = useState('3000')
  const [debts, setDebts] = useState([
    { id: nextId++, name: 'Credit Card', balance: '5000', apr: '22', min_payment: '150' },
    { id: nextId++, name: 'Personal Loan', balance: '10000', apr: '7', min_payment: '200' },
  ])
  const [targetAmount, setTargetAmount] = useState('5000')
  const [targetMonth, setTargetMonth] = useState('24')
  const [horizon, setHorizon] = useState('36')
  const [error, setError] = useState('')

  function updateDebt(id, field, value) {
    setDebts(debts.map((d) => (d.id === id ? { ...d, [field]: value } : d)))
  }

  function addDebt() {
    setDebts([...debts, newDebt()])
  }

  function removeDebt(id) {
    setDebts(debts.filter((d) => d.id !== id))
  }

  function handleSubmit(e) {
    e.preventDefault()
    setError('')

    if (debts.length === 0) {
      setError('Add at least one debt.')
      return
    }

    const payload = {
      monthly_cash: parseFloat(monthlyCash),
      debts: debts.map((d) => ({
        name: d.name || 'Unnamed debt',
        balance: parseFloat(d.balance),
        apr: parseFloat(d.apr) / 100, // user enters "22" meaning 22%
        min_payment: parseFloat(d.min_payment),
      })),
      savings_goal: {
        target_amount: parseFloat(targetAmount) || 0,
        target_month: targetMonth ? parseInt(targetMonth, 10) : null,
      },
      horizon_months: parseInt(horizon, 10) || 36,
    }

    for (const d of payload.debts) {
      if (Number.isNaN(d.balance) || Number.isNaN(d.apr) || Number.isNaN(d.min_payment)) {
        setError('Every debt needs a balance, APR, and minimum payment.')
        return
      }
    }

    onSubmit(payload)
  }

  return (
    <form onSubmit={handleSubmit} className="card">
      <h2>Your finances</h2>

      <label>Monthly cash available for debt + savings</label>
      <input
        type="number"
        step="0.01"
        value={monthlyCash}
        onChange={(e) => setMonthlyCash(e.target.value)}
        required
      />

      <label style={{ marginTop: 10 }}>Debts</label>
      {debts.map((d) => (
        <div className="debt-row" key={d.id}>
          <input
            placeholder="Name"
            value={d.name}
            onChange={(e) => updateDebt(d.id, 'name', e.target.value)}
          />
          <input
            placeholder="Balance ($)"
            type="number"
            step="0.01"
            value={d.balance}
            onChange={(e) => updateDebt(d.id, 'balance', e.target.value)}
          />
          <input
            placeholder="APR (%)"
            type="number"
            step="0.01"
            value={d.apr}
            onChange={(e) => updateDebt(d.id, 'apr', e.target.value)}
          />
          <input
            placeholder="Min payment"
            type="number"
            step="0.01"
            value={d.min_payment}
            onChange={(e) => updateDebt(d.id, 'min_payment', e.target.value)}
          />
          <button type="button" className="danger" onClick={() => removeDebt(d.id)}>
            Remove
          </button>
        </div>
      ))}
      <button type="button" className="secondary" onClick={addDebt} style={{ marginBottom: 16 }}>
        + Add another debt
      </button>

      <label>Savings goal</label>
      <div className="row">
        <input
          placeholder="Target amount ($)"
          type="number"
          step="0.01"
          value={targetAmount}
          onChange={(e) => setTargetAmount(e.target.value)}
        />
        <input
          placeholder="Deadline (months)"
          type="number"
          value={targetMonth}
          onChange={(e) => setTargetMonth(e.target.value)}
        />
      </div>

      <label>Simulation horizon (months)</label>
      <input type="number" value={horizon} onChange={(e) => setHorizon(e.target.value)} />

      {error && <div className="error-box">{error}</div>}

      <button type="submit" disabled={loading}>
        {loading ? 'Optimizing…' : 'Get my optimal plan'}
      </button>
    </form>
  )
}
