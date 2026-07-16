import { createLineWrapMark } from './lineWrapMark'

// See lineWrapMark.ts for why this is a Mark and not the built-in Heading
// node.
export const Heading3Mark = createLineWrapMark('heading3', 'h3')
