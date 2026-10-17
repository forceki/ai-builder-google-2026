import { ref } from 'vue'
import { api } from '../api/client'

export function useOpenFile() {
  const error = ref('')

  async function openFile(projectNo, doc, page) {
    error.value = ''
    const tab = window.open('', '_blank')
    try {
      const { url } = await api.documents.link(projectNo, doc.id)
      const target = page && doc.content_type === 'application/pdf' ? `${url}#page=${page}` : url
      if (tab) {
        tab.opener = null
        tab.location.href = target
      } else {
        window.location.assign(target)
      }
    } catch (e) {
      tab?.close()
      error.value = `Could not open ${doc.filename}: ${e.message}`
    }
  }

  return { openFile, error }
}
