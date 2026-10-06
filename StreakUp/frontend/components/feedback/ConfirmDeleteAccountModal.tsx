"use client";

/**
 * ConfirmDeleteAccountModal
 *
 * A two-step destructive-action modal that:
 *   1. Warns the user clearly what will be deleted.
 *   2. Requires typing "ELIMINAR" to unlock the confirm button.
 *   3. Shows a loading state while the API call is in-flight.
 *   4. Surfaces any error message inline so the user doesn't lose context.
 *
 * Props:
 *   isOpen    – controls visibility (parent owns this state)
 *   onClose   – called when the user cancels or clicks outside
 *   onConfirm – async callback; parent calls deleteAccount() + clearSession()
 */

import { useState, useEffect, useRef } from "react";
import { AlertTriangle, X, Trash2 } from "lucide-react";

const CONFIRMATION_WORD = "ELIMINAR";

interface ConfirmDeleteAccountModalProps {
  isOpen: boolean;
  onClose: () => void;
  /** Must be an async function; the modal manages its own loading state. */
  onConfirm: () => Promise<void>;
}

export function ConfirmDeleteAccountModal({
  isOpen,
  onClose,
  onConfirm,
}: ConfirmDeleteAccountModalProps) {
  const [confirmText, setConfirmText] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Reset state every time the modal opens.
  useEffect(() => {
    if (isOpen) {
      setConfirmText("");
      setError(null);
      setIsDeleting(false);
      // Focus the input after the next paint so it is visible.
      setTimeout(() => inputRef.current?.focus(), 80);
    }
  }, [isOpen]);

  // Close on Escape key.
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !isDeleting) {
        onClose();
      }
    }
    if (isOpen) {
      document.addEventListener("keydown", handleKey);
    }
    return () => document.removeEventListener("keydown", handleKey);
  }, [isOpen, isDeleting, onClose]);

  const canConfirm = confirmText === CONFIRMATION_WORD && !isDeleting;

  async function handleConfirm() {
    if (!canConfirm) return;
    setIsDeleting(true);
    setError(null);
    try {
      await onConfirm();
      // onConfirm is expected to redirect; no need to close the modal here.
    } catch (err) {
      setError(
        err instanceof Error && err.message.trim()
          ? err.message
          : "No se pudo eliminar la cuenta. Inténtalo de nuevo.",
      );
      setIsDeleting(false);
    }
  }

  if (!isOpen) return null;

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4"
      aria-modal="true"
      role="dialog"
      aria-labelledby="delete-account-title"
    >
      {/* Dim overlay */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={() => !isDeleting && onClose()}
        aria-hidden="true"
      />

      {/* Panel */}
      <div className="relative z-10 w-full max-w-md rounded-2xl border border-red-500/30 bg-[#111127] shadow-2xl p-6 space-y-5">
        {/* Close button */}
        <button
          onClick={onClose}
          disabled={isDeleting}
          className="absolute top-4 right-4 text-muted-foreground hover:text-white transition-colors disabled:opacity-40"
          aria-label="Cerrar"
        >
          <X className="size-5" />
        </button>

        {/* Header */}
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 size-10 rounded-xl bg-red-500/20 flex items-center justify-center">
            <AlertTriangle className="size-5 text-red-400" />
          </div>
          <div>
            <h2
              id="delete-account-title"
              className="text-base font-bold text-white"
            >
              Eliminar cuenta permanentemente
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Esta acción no se puede deshacer.
            </p>
          </div>
        </div>

        {/* Warning list */}
        <ul className="text-sm text-red-300/90 space-y-1.5 list-disc list-inside">
          <li>Todos tus hábitos y configuraciones serán eliminados.</li>
          <li>Tu historial de check-ins y rachas desaparecerá.</li>
          <li>Tus puntos de XP y logros se perderán para siempre.</li>
          <li>No podrás recuperar tu cuenta.</li>
        </ul>

        {/* Confirmation input */}
        <div className="space-y-1.5">
          <label
            htmlFor="delete-confirm-input"
            className="text-xs font-medium text-muted-foreground"
          >
            Escribe{" "}
            <span className="font-bold text-red-400 tracking-wide">
              {CONFIRMATION_WORD}
            </span>{" "}
            para confirmar:
          </label>
          <input
            ref={inputRef}
            id="delete-confirm-input"
            type="text"
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value.toUpperCase())}
            disabled={isDeleting}
            autoComplete="off"
            spellCheck={false}
            placeholder={CONFIRMATION_WORD}
            className="w-full h-11 rounded-xl border border-[#2A2A3E] bg-[#1A1A2E] px-4 text-sm font-mono text-white placeholder:text-muted-foreground/40 focus:outline-none focus:ring-2 focus:ring-red-500/50 disabled:opacity-50"
          />
        </div>

        {/* Inline error */}
        {error && (
          <p className="text-xs text-red-400 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2">
            {error}
          </p>
        )}

        {/* Actions */}
        <div className="flex gap-3 pt-1">
          <button
            onClick={onClose}
            disabled={isDeleting}
            className="flex-1 h-11 rounded-xl border border-[#2A2A3E] bg-transparent text-sm font-semibold text-white hover:bg-[#1A1A2E] transition-colors disabled:opacity-40"
          >
            Cancelar
          </button>
          <button
            onClick={() => void handleConfirm()}
            disabled={!canConfirm}
            className="flex-1 h-11 rounded-xl bg-red-600 hover:bg-red-700 text-sm font-semibold text-white transition-colors flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isDeleting ? (
              <div className="size-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <>
                <Trash2 className="size-4" />
                Eliminar cuenta
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
