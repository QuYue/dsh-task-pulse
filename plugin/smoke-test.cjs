// Smoke test for the client bundle wiring without a DSH host.
const fs = require('fs')
const vm = require('vm')
const path = require('path')

const file = path.join(__dirname, 'lib', 'client.js')
const captured = { id: null, spec: null, component: null }
const sandbox = {
  console,
  document: {
    getElementById: () => null,
    createElement: () => ({ style: {}, appendChild() {}, setAttribute() {} }),
    head: { appendChild() {} },
  },
  window: {
    __ModuleLoader__: {
      load(entry) {
        captured.id = entry.id
        const require = (name) => name === 'react'
          ? { createElement: () => ({}), useState: () => [] }
          : {}
        captured.exports = entry.factory(require)
      },
    },
  },
}
vm.createContext(sandbox)
vm.runInContext(fs.readFileSync(file, 'utf8'), sandbox)

function assert(condition, message) {
  if (!condition) throw new Error(message)
  console.log('ok -', message)
}

assert(captured.id === 'dsh-live-progress-card', 'bundle id')
assert(typeof captured.exports.apply === 'function', 'exports.apply is a function')
assert(Array.isArray(captured.exports.inject), 'exports.inject is an array')

captured.exports.apply({
  slots: {
    inject(name, register) { assert(name === 'conversation.input.dock', 'slot name'); register() },
    register(spec, component) { captured.spec = spec; captured.component = component },
  },
})
assert(captured.spec.name === 'conversation.input.dock', 'registers on composer input dock')
assert(captured.spec.id === 'live-progress-card', 'slot entry id')
assert(captured.spec.order === 1, 'slot order after native todo (0)')
assert(typeof captured.component === 'function', 'slot component is a function')
console.log('client bundle smoke test passed')
