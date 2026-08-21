// One UUID minter for the analytics slice.
//
// `crypto.randomUUID` where it exists — every browser this app is served to, over the secure
// origin it is served from. The fallback is not decoration: it is what runs on an insecure-origin
// preview build and in a test environment without the Web Crypto API, and a thrown TypeError
// there would take a page down for the sake of an analytics identifier.
//
// Shared rather than copied, because the two callers mint for different reasons — a visitor id
// that must persist and an occurrence key that must not — and a second copy is where one of them
// quietly stops being a valid v4 while its own tests still pass.
export function mintUuid(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (character) => {
    const random = Math.trunc(Math.random() * 16)
    const value = character === 'x' ? random : (random & 0x3) | 0x8
    return value.toString(16)
  })
}
