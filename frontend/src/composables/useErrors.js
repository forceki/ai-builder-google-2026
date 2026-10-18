import { reactive } from 'vue'

// App-wide error list: anything that fails without its own handling is shown, never only logged.
export const errors = reactive([])
let seq = 0

export function reportError(err, context = '') {
  const message = (err && (err.message || err.reason?.message)) || String(err || 'Unknown error')
  console.error(context || 'Unhandled error', err)
  // The same message twice in a row is one problem, not two.
  if (errors.length && errors[errors.length - 1].message === message) return
  errors.push({ id: ++seq, message, context, at: new Date() })
  if (errors.length > 5) errors.shift()
}

export const dismissError = (id) => {
  const i = errors.findIndex((e) => e.id === id)
  if (i >= 0) errors.splice(i, 1)
}
