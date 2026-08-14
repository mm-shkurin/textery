// What the server will actually see, and how long it will actually think it is.
//
// Both answers have to be computed on the SAME value the domain bounds, which is the value after
// trim and NFC — not the raw field contents. Two ways to get this wrong, both silent:
//
//   - Counting `value.length` counts UTF-16 units. A name of 60 emoji reads 120, the counter goes
//     red and «Сохранить» stays off — on a name the server would accept with a 200.
//   - Counting the RAW value counts before normalization. A name typed on a keyboard that emits
//     NFD (macOS, Vietnamese and Korean IMEs) is up to twice as long decomposed as composed, so
//     the same 60 visible characters read 120 and are refused locally for the same reason.
//
// The domain bound is 60 code points after trim + NFC; the raw cap is 256 code points before it.
export const NAME_MAX_CODE_POINTS = 60
export const RAW_NAME_MAX_CODE_POINTS = 256

export function normalizeName(value: string): string {
  return value.trim().normalize('NFC')
}

export function countCodePoints(value: string): number {
  return [...value].length
}

// The dirty flag, and it is computed against the SAVED profile's name — which after a save is
// whatever the PATCH response returned, i.e. the normalized value. Comparing against what was
// typed instead leaves a name with a trailing space permanently "unsaved": the field holds
// `"Анна "`, the server stored `"Анна"`, and no amount of saving makes them equal.
export function isNameChanged(value: string, savedName: string | null): boolean {
  return normalizeName(value) !== (savedName ?? '')
}
