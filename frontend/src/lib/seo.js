// Per-page title, description, canonical URL and robots tag. Search engines render the SPA, so these are set on every
// navigation from the route's `seo` meta. Signed-in pages are noindex: they hold private projects and no content to rank.
export const SITE_URL = 'https://hibanako.web.app'
export const DEFAULT_TITLE = 'Hibanako — AI Weld Quality Documentation & Traceability'
export const DEFAULT_DESCRIPTION =
  'Hibanako uses Google Gemini to read welding documents (mill certificates, WPS and PQR, welder qualifications, PWHT and NDT reports) and checks every weld against your governing code.'

// The head element matching `selector`, created with `attrs` when index.html doesn't have it.
function headTag(name, selector, attrs) {
  let el = document.head.querySelector(selector)
  if (!el) {
    el = document.createElement(name)
    for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v)
    document.head.appendChild(el)
  }
  return el
}

const setMeta = (attr, key, content) =>
  headTag('meta', `meta[${attr}="${key}"]`, { [attr]: key }).setAttribute('content', content)

export function applySeo(route) {
  const seo = route.meta.seo || {}
  const title = seo.title ? `${seo.title} — Hibanako` : DEFAULT_TITLE
  const description = seo.description || DEFAULT_DESCRIPTION
  const url = SITE_URL + (seo.index ? route.path : '/')

  document.title = title
  setMeta('name', 'description', description)
  setMeta('name', 'robots', seo.index ? 'index, follow' : 'noindex, nofollow')
  setMeta('property', 'og:title', title)
  setMeta('property', 'og:description', description)
  setMeta('property', 'og:url', url)
  setMeta('name', 'twitter:title', title)
  setMeta('name', 'twitter:description', description)
  headTag('link', 'link[rel="canonical"]', { rel: 'canonical' }).setAttribute('href', url)
}
