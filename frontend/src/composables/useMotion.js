import { onBeforeUnmount, onMounted } from 'vue'

// Scroll-triggered motion for [data-draw] SVG strokes, [data-reveal] blocks
// and [data-stamp] status stamps (optional data-rot = final rotation in deg).
export function useMotion(enabled = true) {
  let io

  onMounted(() => {
    if (!enabled) return
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return
    if (!('IntersectionObserver' in window)) return

    const prep = []
    document.querySelectorAll('[data-draw]').forEach((el) => {
      let len = 0
      try {
        len = el.getTotalLength ? el.getTotalLength() : 0
      } catch (e) {}
      if (!len) return
      el.style.strokeDasharray = len
      el.style.strokeDashoffset = len
      prep.push({ el, run: () => { el.style.transition = 'stroke-dashoffset 1.4s cubic-bezier(.4,0,.2,1)'; el.style.strokeDashoffset = 0 } })
    })
    document.querySelectorAll('[data-reveal]').forEach((el) => {
      el.style.opacity = 0
      el.style.transform = 'translateY(10px)'
      prep.push({ el, run: () => { el.style.transition = 'opacity .6s ease, transform .6s ease'; el.style.opacity = 1; el.style.transform = 'none' } })
    })
    document.querySelectorAll('[data-stamp]').forEach((el) => {
      const rot = el.getAttribute('data-rot')
      const final = rot ? `rotate(${rot}deg)` : 'none'
      el.style.opacity = 0
      el.style.transform = 'scale(1.5)' + (rot ? ` rotate(${rot}deg)` : '')
      prep.push({ el, delay: 500, run: () => { el.style.transition = 'opacity .18s ease-out, transform .22s cubic-bezier(.3,0,.2,1)'; el.style.opacity = 1; el.style.transform = final } })
    })

    const map = new Map(prep.map((p) => [p.el, p]))
    io = new IntersectionObserver((entries) => {
      entries.forEach((en) => {
        if (!en.isIntersecting) return
        const p = map.get(en.target)
        io.unobserve(en.target)
        if (p) setTimeout(p.run, p.delay || 0)
      })
    }, { threshold: 0.15 })
    prep.forEach((p) => io.observe(p.el))
  })

  onBeforeUnmount(() => io?.disconnect())
}
