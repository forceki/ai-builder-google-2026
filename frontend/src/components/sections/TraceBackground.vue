<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'

const canvas = ref(null)
let ctx = null
let raf = null
let scanTimer = null
const B = { w: 0, h: 0, mx: 0, my: 0, tx: 0, ty: 0, px: null, py: null, lastMove: -1e9, nodes: [] }
const still = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

function resize() {
  const d = Math.min(2, devicePixelRatio || 1)
  B.w = innerWidth
  B.h = innerHeight
  canvas.value.width = B.w * d
  canvas.value.height = B.h * d
  ctx.setTransform(d, 0, 0, d, 0, 0)
  if (still) draw(0)
}

function move(e) {
  B.tx = e.clientX / B.w - 0.5
  B.ty = e.clientY / B.h - 0.5
  B.px = e.clientX
  B.py = e.clientY
  B.lastMove = performance.now()
}

function scan() {
  const prev = B.nodes
  B.nodes = [...document.querySelectorAll('[data-trace-node]')].map((el, i) => {
    const r = el.getBoundingClientRect()
    return {
      n: el.dataset.traceNum,
      label: el.dataset.traceLabel,
      x: r.left,
      y: r.top + r.height / 2 + scrollY,
      on: prev[i]?.on ?? 0,
    }
  })
}

function palette() {
  const css = getComputedStyle(document.documentElement)
  const shade = (css.getPropertyValue('--shade').trim() || '17 17 17').split(/\s+/).join(',')
  return {
    ink: (a) => `rgba(${shade},${a})`,
    solidInk: css.getPropertyValue('--color-ink').trim() || '#111111',
    paper: css.getPropertyValue('--color-paper').trim() || '#edeae3',
    signal: css.getPropertyValue('--color-signal').trim() || '#ff4f00',
  }
}

function draw(t) {
  const { w, h } = B
  const sy = scrollY
  const c = palette()
  B.mx += (B.tx - B.mx) * 0.05
  B.my += (B.ty - B.my) * 0.05
  ctx.clearRect(0, 0, w, h)

  for (const [g, k, a, r] of [[48, 0.25, 0.07, 0.9], [24, 0.55, 0.13, 0.7]]) {
    const oy = -((sy * k) % g)
    const ox = (B.mx * 12 * k) % g
    ctx.fillStyle = c.ink(a)
    for (let y = oy; y < h + g; y += g) {
      for (let x = ox; x < w + g; x += g) {
        ctx.beginPath()
        ctx.arc(x, y, r, 0, 6.283)
        ctx.fill()
      }
    }
  }
  const g2 = 120
  const oy2 = -((sy * 0.55) % g2)
  const ox2 = (B.mx * 6.6) % g2
  ctx.strokeStyle = c.ink(0.16)
  ctx.lineWidth = 1
  for (let y = oy2; y < h + g2; y += g2) {
    for (let x = ox2; x < w + g2; x += g2) {
      ctx.beginPath()
      ctx.moveTo(x - 4, y)
      ctx.lineTo(x + 4, y)
      ctx.moveTo(x, y - 4)
      ctx.lineTo(x, y + 4)
      ctx.stroke()
    }
  }

  const N = B.nodes
  if (N.length) {
    const left = Math.min(...N.map((n) => n.x))
    const sx = Math.max(8, left - Math.min(26, left * 0.55))
    const top = 70
    const head = sy + h * 0.6
    const last = N[N.length - 1].y
    const end = Math.min(head, last)

    ctx.strokeStyle = c.ink(0.18)
    ctx.setLineDash([2, 4])
    ctx.beginPath()
    ctx.moveTo(sx, top - sy)
    ctx.lineTo(sx, last - sy)
    ctx.stroke()
    ctx.setLineDash([])
    ctx.strokeStyle = c.signal
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.moveTo(sx, top - sy)
    ctx.lineTo(sx, end - sy)
    ctx.stroke()

    let cur = N[0]
    ctx.font = "500 10px 'JetBrains Mono', monospace"
    ctx.textBaseline = 'middle'
    for (const n of N) {
      const passed = head >= n.y
      if (passed) cur = n
      n.on += ((passed ? 1 : 0) - n.on) * (still ? 1 : 0.12)
      const y = n.y - sy
      if (y < -20 || y > h + 20) continue
      const stub = (n.x - 8 - sx) * n.on
      if (stub > 1) {
        ctx.strokeStyle = c.signal
        ctx.lineWidth = 2
        ctx.beginPath()
        ctx.moveTo(sx, y)
        ctx.lineTo(sx + stub, y)
        ctx.stroke()
      }
      ctx.lineWidth = 1
      ctx.strokeStyle = c.solidInk
      ctx.fillStyle = n.on > 0.5 ? c.signal : c.paper
      ctx.beginPath()
      ctx.arc(sx, y, 4.5, 0, 6.283)
      ctx.fill()
      ctx.stroke()
    }

    const hy = end - sy
    const pulse = still ? 0 : (t * 0.0015) % 1
    if (head < last + 4) {
      ctx.globalAlpha = 1 - pulse
      ctx.strokeStyle = c.signal
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.arc(sx, hy, 5 + pulse * 12, 0, 6.283)
      ctx.stroke()
      ctx.globalAlpha = 1
      ctx.fillStyle = c.signal
      ctx.strokeStyle = c.solidInk
      ctx.beginPath()
      ctx.arc(sx, hy, 4, 0, 6.283)
      ctx.fill()
      ctx.stroke()
    }

    ctx.fillStyle = c.ink(0.6)
    ctx.save()
    ctx.translate(Math.max(5, sx - 12), h - 24)
    ctx.rotate(-Math.PI / 2)
    const pct = Math.round(Math.min(1, Math.max(0, (end - top) / (last - top))) * 100)
    ctx.fillText(`TRACE ${cur.n} · ${cur.label} · ${pct}%`, 0, 0)
    ctx.restore()
  }

  const idle = performance.now() - B.lastMove
  const ca = Math.max(0, 1 - Math.max(0, idle - 900) / 600)
  if (ca > 0 && B.px != null) {
    ctx.globalAlpha = ca
    ctx.strokeStyle = c.ink(0.1)
    ctx.lineWidth = 1
    ctx.setLineDash([3, 5])
    ctx.beginPath()
    ctx.moveTo(0, B.py + 0.5)
    ctx.lineTo(w, B.py + 0.5)
    ctx.moveTo(B.px + 0.5, 0)
    ctx.lineTo(B.px + 0.5, h)
    ctx.stroke()
    ctx.setLineDash([])
    ctx.fillStyle = c.ink(0.55)
    ctx.font = "500 10px 'JetBrains Mono', monospace"
    ctx.textBaseline = 'middle'
    ctx.fillText(
      `X ${String(Math.round(B.px)).padStart(4, '0')}  Y ${String(Math.round(B.py + sy)).padStart(5, '0')}`,
      B.px + 12,
      B.py + 14,
    )
    ctx.globalAlpha = 1
  }
}

function frame(t) {
  draw(t)
  raf = requestAnimationFrame(frame)
}

const redrawStill = () => draw(0)

onMounted(() => {
  ctx = canvas.value.getContext('2d')
  resize()
  scan()
  scanTimer = setInterval(scan, 1200)
  addEventListener('resize', resize)
  addEventListener('mousemove', move)
  if (still) addEventListener('scroll', redrawStill, { passive: true })
  else raf = requestAnimationFrame(frame)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  clearInterval(scanTimer)
  removeEventListener('resize', resize)
  removeEventListener('mousemove', move)
  removeEventListener('scroll', redrawStill)
})
</script>

<template>
  <canvas ref="canvas" aria-hidden="true" class="pointer-events-none fixed inset-0 z-0 h-full w-full print:hidden"></canvas>
</template>
