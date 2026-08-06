// What the user fills in on the generation form, beyond the topic. One type rather than three
// more positional arguments threaded through Composer -> ChatWorkspace -> useGeneration ->
// generationApi: at four call sites, positional strings are transposable and the transposition
// type-checks (`requirements` and `extraWishes` are both `string`).
//
// The fields are the mockup's (`mockups/desktop/04-generation-form.html`) and the domain's:
// `Generation.create` validates volume 1..10 and caps both texts at 2000 characters.
export interface GenerationParameters {
  volumePages: number
  requirements: string
  extraWishes: string
}

// The mockup's default (`<input type="number" min="1" max="10" value="5">`) and the value the
// client hardcoded before the field existed, so an untouched form still asks for what it always
// asked for.
export const DEFAULT_VOLUME_PAGES = 5
export const MIN_VOLUME_PAGES = 1
export const MAX_VOLUME_PAGES = 10

// The domain's caps (`MAX_REQUIREMENTS_LENGTH` / `MAX_EXTRA_WISHES_LENGTH`). Mirrored here so the
// textarea stops accepting text the server would refuse — a `maxLength` the user meets is a
// better answer than a 400 after they wrote 3000 characters.
export const MAX_REQUIREMENTS_LENGTH = 2000
export const MAX_EXTRA_WISHES_LENGTH = 2000

export const EMPTY_PARAMETERS: GenerationParameters = {
  volumePages: DEFAULT_VOLUME_PAGES,
  requirements: '',
  extraWishes: '',
}

/** True when the volume is an integer inside the range the server accepts. */
export function isVolumeAcceptable(volumePages: number): boolean {
  return Number.isInteger(volumePages) && volumePages >= MIN_VOLUME_PAGES && volumePages <= MAX_VOLUME_PAGES
}
