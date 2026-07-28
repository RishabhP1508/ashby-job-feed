import { useEffect, useRef, useState } from 'react'
import type { User } from '../types'
import { AuthPanel } from './AuthPanel'

interface Props {
  onAuth: (user: User) => void
}

// Native popover: the browser handles light-dismiss (outside click), Escape,
// and focus restoration to the trigger. The `toggle` listener only keeps
// aria-expanded in sync and moves focus into the form when it opens.
export function AuthPopover({ onAuth }: Props) {
  const popRef = useRef<HTMLDivElement>(null)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const el = popRef.current
    if (!el) return
    const onToggle = (event: Event) => {
      const isOpen = (event as ToggleEvent).newState === 'open'
      setOpen(isOpen)
      if (isOpen) el.querySelector<HTMLInputElement>('input')?.focus()
    }
    el.addEventListener('toggle', onToggle)
    return () => el.removeEventListener('toggle', onToggle)
  }, [])

  return (
    <div className="auth-slot">
      <button
        type="button"
        className="btn btn-login"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls="auth-popover"
        onClick={() => popRef.current?.togglePopover()}
      >
        Log in
      </button>
      <div
        ref={popRef}
        id="auth-popover"
        className="auth-popover"
        role="dialog"
        aria-label="Log in or create an account"
        popover="auto"
      >
        <AuthPanel
          onAuth={(user) => {
            popRef.current?.hidePopover()
            onAuth(user)
          }}
        />
      </div>
    </div>
  )
}
