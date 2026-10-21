// Vuetify usa APIs del navegador que jsdom no implementa.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverStub as unknown as typeof ResizeObserver

// Los diálogos de Vuetify consultan el viewport visual.
Object.defineProperty(globalThis, 'visualViewport', {
  value: { width: 1024, height: 768, offsetLeft: 0, offsetTop: 0, scale: 1, addEventListener() {}, removeEventListener() {} },
  configurable: true,
})
