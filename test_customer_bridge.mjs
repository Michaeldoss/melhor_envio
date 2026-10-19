import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import assert from 'node:assert/strict'
const source = readFileSync(new URL('./app.py', import.meta.url), 'utf8')
const fullScript = source.split('<script>')[1].split('</script>')[0]
new Function(fullScript)
const bridge = fullScript.split('    const form =')[0]
const elements = new Map()
const el = id => {
  if (!elements.has(id)) elements.set(id, { value: '', textContent: '', disabled: false, listeners: {}, addEventListener(type, fn) { this.listeners[type] = fn } })
  return elements.get(id)
}
const sent = [], messages = [], parent = { postMessage: (data, origin) => sent.push({data, origin}) }
let sequence = 0
const window = { parent, addEventListener: (type, fn) => { if(type === 'message') messages.push(fn) } }
vm.runInNewContext(bridge, { window, document: { getElementById: el }, crypto: { randomUUID: () => `request-${++sequence}` }, setTimeout: () => 1, clearTimeout: () => {} })
el('customer_code').value = '2174'
el('customer_lookup').listeners.click()
assert.equal(sent[0].origin, 'https://doss-crm.vercel.app')
assert.equal(sent[0].data.code, '2174')
const receive = (origin, id = sent.at(-1).data.requestId, customer = {name:'Cliente A',cep:'85803630',document:'12345678000190'}, source = parent) => messages[0]({origin,source,data:{type:'doss:customer-result',requestId:id,customer}})
receive('https://evil.example')
assert.equal(el('to_postal_code').value,'')
receive('https://doss-crm.vercel.app','old-request')
assert.equal(el('to_postal_code').value,'')
receive('https://doss-crm.vercel.app',sent.at(-1).data.requestId,undefined,{})
assert.equal(el('to_postal_code').value,'')
receive('https://doss-crm.vercel.app')
assert.equal(el('to_postal_code').value,'85803-630')
assert.equal(el('recipient_doc').value,'12345678000190')
el('customer_code').listeners.input()
assert.equal(el('to_postal_code').value,'')
assert.equal(el('recipient_doc').value,'')
el('customer_lookup').listeners.click()
const stale=sent.at(-1).data.requestId
el('customer_code').listeners.input()
receive('https://doss-crm.vercel.app',stale)
assert.equal(el('to_postal_code').value,'')
el('customer_lookup').listeners.click()
receive('https://doss-crm.vercel.app',sent.at(-1).data.requestId,{name:'Sem cadastro completo',cep:'',document:''})
assert.match(el('customer_lookup_status').textContent,/CEP ausente.*CNPJ\/CPF ausente/)
el('customer_code').value='2174 OR 1=1'
const before=sent.length
el('customer_lookup').listeners.click()
assert.equal(sent.length,before)
console.log('12 freight field, origin, source and stale-response checks passed')
