import { createStore } from 'vuex'
import theme from './modules/theme'
import demo from './modules/demo'
import report from './modules/report'
import auth from './modules/auth'
import projects from './modules/projects'
import workspace from './modules/workspace'
import release from './modules/release'

export default createStore({
  strict: import.meta.env.DEV,
  modules: { theme, demo, report, auth, projects, workspace, release },
})
