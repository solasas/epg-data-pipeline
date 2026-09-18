import { useEffect, useMemo, useState } from 'react'
import { getChannels, getNowAiring, getSchedule } from './api'
import './App.css'

function formatTime(iso) {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function App() {
  const [channels, setChannels] = useState([])
  const [nowAiring, setNowAiring] = useState([])
  const [selectedChannel, setSelectedChannel] = useState('')
  const [date, setDate] = useState('')
  const [schedule, setSchedule] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getChannels().then(setChannels).catch((err) => setError(err.message))
    getNowAiring().then((rows) => setNowAiring(rows ?? [])).catch((err) => setError(err.message))
  }, [])

  useEffect(() => {
    setError(null)
    getSchedule({ channelId: selectedChannel || undefined, date: date || undefined })
      .then(setSchedule)
      .catch((err) => setError(err.message))
  }, [selectedChannel, date])

  const nowAiringByChannel = useMemo(() => {
    const map = new Map()
    for (const p of nowAiring) map.set(p.channel_id, p)
    return map
  }, [nowAiring])

  return (
    <div className="epg">
      <h1>Electronic Program Guide</h1>

      {error && <p className="error">{error}</p>}

      <div className="filters">
        <select value={selectedChannel} onChange={(e) => setSelectedChannel(e.target.value)}>
          <option value="">All channels</option>
          {channels.map((c) => (
            <option key={c.channel_id} value={c.channel_id}>
              {c.display_name}
            </option>
          ))}
        </select>
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
      </div>

      <section>
        <h2>Now Airing</h2>
        <ul className="now-airing">
          {channels
            .filter((c) => !selectedChannel || c.channel_id === selectedChannel)
            .map((c) => {
            const p = nowAiringByChannel.get(c.channel_id)
            return (
              <li key={c.channel_id}>
                <strong>{c.display_name}</strong>
                {p ? ` — ${p.title} (${formatTime(p.start_time)}–${formatTime(p.stop_time)})` : ' — off air'}
              </li>
            )
          })}
        </ul>
      </section>

      <section>
        <h2>Schedule</h2>
        {!schedule && <p>No programmes found.</p>}
        {schedule && (
          <table>
            <thead>
              <tr>
                <th>Channel</th>
                <th>Time</th>
                <th>Title</th>
                <th>Category</th>
              </tr>
            </thead>
            <tbody>
              {schedule.results.map((p) => (
                <tr key={`${p.channel_id}-${p.start_time}`}>
                  <td>{p.channel_id}</td>
                  <td>{formatTime(p.start_time)}–{formatTime(p.stop_time)}</td>
                  <td>{p.title}</td>
                  <td>{p.category}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  )
}

export default App
