const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

async function getJSON(path) {
  const res = await fetch(`${API_BASE}${path}`)
  if (res.status === 404) return null
  if (!res.ok) throw new Error(`Request to ${path} failed: ${res.status}`)
  return res.json()
}

export function getChannels() {
  return getJSON('/channels')
}

export function getSchedule({ channelId, date, category, limit = 50, offset = 0 } = {}) {
  const params = new URLSearchParams()
  if (channelId) params.set('channel_id', channelId)
  if (date) params.set('date', date)
  if (category) params.set('category', category)
  params.set('limit', limit)
  params.set('offset', offset)
  return getJSON(`/schedule?${params.toString()}`)
}

export function getNowAiring() {
  return getJSON('/schedule/now')
}
