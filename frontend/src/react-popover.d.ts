import 'react'

// The native Popover API attributes ship in react-dom 18.3 at runtime but are
// only declared in @types/react's canary types, not the stable HTMLAttributes.
// Declare them so JSX using `popover` typechecks. The imperative methods
// (showPopover/hidePopover/togglePopover) are already in lib.dom (TS 5.5+).
declare module 'react' {
  interface HTMLAttributes<T> {
    popover?: 'auto' | 'manual' | ''
  }
}
