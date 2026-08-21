import { TEXT_STYLES, TEXT_STYLE_OPTIONS, type TextStyle } from '../../../shared/domain/textStyles'
import {
  DEFAULT_VOLUME_PAGES,
  MAX_VOLUME_PAGES,
  MIN_VOLUME_PAGES,
  isVolumeAcceptable,
} from '../../../shared/domain/volumePages'

// Re-exported, not redefined: both vocabularies live in `shared/` because the projects feature
// needs them too (the register and the length are both re-chosen on a retry), and this feature's
// own callers should not have to know where they moved.
export { TEXT_STYLES, TEXT_STYLE_OPTIONS }
export type { TextStyle }
export { DEFAULT_VOLUME_PAGES, MAX_VOLUME_PAGES, MIN_VOLUME_PAGES, isVolumeAcceptable }

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
  // '' means «не выбран» — the register the model picks on its own. Kept as the empty string
  // rather than `null` because it is the value a `<select>` reports for its placeholder option,
  // and translating at the boundary (below) is one conversion instead of one per render.
  textStyle: TextStyle | ''
}

// The domain's caps (`MAX_REQUIREMENTS_LENGTH` / `MAX_EXTRA_WISHES_LENGTH`). Mirrored here so the
// textarea stops accepting text the server would refuse — a `maxLength` the user meets is a
// better answer than a 400 after they wrote 3000 characters.
export const MAX_REQUIREMENTS_LENGTH = 2000
export const MAX_EXTRA_WISHES_LENGTH = 2000

export const EMPTY_PARAMETERS: GenerationParameters = {
  volumePages: DEFAULT_VOLUME_PAGES,
  requirements: '',
  extraWishes: '',
  // Deliberately not defaulted to 'научный'. Preselecting a register would send it on every
  // untouched form, recording a choice the user never made — and «не выбран» is a real, different
  // instruction to the model, not a missing value to be filled in.
  textStyle: '',
}
