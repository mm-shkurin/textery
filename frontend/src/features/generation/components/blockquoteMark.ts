import { createLineWrapMark } from './lineWrapMark'

// See lineWrapMark.ts for why this is a Mark and not the built-in Blockquote
// node.
export const BlockquoteMark = createLineWrapMark('blockquote', 'blockquote')
