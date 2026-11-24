"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/features/auth/AuthForm";
import { PASSWORD_HINT, passwordValid } from "@/features/auth/rules";
import { memberRequest } from "@/features/auth/session";
import { apiFetch } from "@/lib/api/client";
import { isApiError } from "@/lib/api/errors";
import type { Member, PasswordChange } from "@/lib/api/types";
import { PASSWORD_FAILED_TEXT, localPasswordError, passwordFieldError, type PasswordField } from "./model";

const EMPTY: PasswordChange = { currentPassword: "", newPassword: "", newPasswordConfirm: "" };

const FIELDS: { name: PasswordField; label: string; placeholder: string; autoComplete: string }[] = [
  { name: "currentPassword", label: "현재 비밀번호", placeholder: "현재 비밀번호 입력", autoComplete: "current-password" },
  { name: "newPassword", label: "새 비밀번호", placeholder: "새 비밀번호 입력", autoComplete: "new-password" },
  { name: "newPasswordConfirm", label: "새 비밀번호 확인", placeholder: "새 비밀번호 다시 입력", autoComplete: "new-password" },
];

/**
 * 비밀번호 변경 (MY-004 rule 2, Figma 643:658 / 643:755, states 639:7452): centred dialog from
 * 1024px, bottom sheet below. Default · CurrentError · RuleError · ConfirmError (one code, one
 * field) · Saving (inputs, buttons and closing locked) · Failed (429 / network / 5xx: the
 * input stays, '다시 시도'). Success closes it; the account area shows the notice. The server
 * keeps this browser signed in and ends the other sessions.
 */
export function PasswordDialog({ open, onClose, onDone }: { open: boolean; onClose: () => void; onDone: () => void }) {
  const [values, setValues] = useState<PasswordChange>(EMPTY);
  const [fieldError, setFieldError] = useState<{ field: PasswordField; message: string } | null>(null);
  const [phase, setPhase] = useState<"idle" | "saving" | "failed">("idle");
  const form = useRef<HTMLFormElement>(null);
  const saving = phase === "saving";
  const filled = Object.values(values).every(Boolean);

  // Opening starts in the first field (after the dialog has taken focus itself).
  useEffect(() => {
    if (!open) return;
    const frame = requestAnimationFrame(() => form.current?.querySelector<HTMLInputElement>("input")?.focus());
    return () => cancelAnimationFrame(frame);
  }, [open]);

  // A field error moves focus to that field so its message is read with it.
  useEffect(() => {
    if (fieldError) form.current?.querySelector<HTMLInputElement>("[aria-invalid=true]")?.focus();
  }, [fieldError]);

  // Passwords are never kept after the dialog closes.
  const close = () => {
    if (saving) return;
    setValues(EMPTY);
    setFieldError(null);
    setPhase("idle");
    onClose();
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (saving || !filled) return;
    const local = localPasswordError(passwordValid(values.newPassword), values.newPassword, values.newPasswordConfirm);
    if (local) {
      setFieldError(local);
      setPhase("idle");
      return;
    }
    setFieldError(null);
    setPhase("saving");
    try {
      await memberRequest(() => apiFetch<Member>("/me/password", { method: "PATCH", body: values }));
      setPhase("idle");
      setValues(EMPTY);
      onDone();
    } catch (caught) {
      if (isApiError(caught) && caught.status === 401) {
        // The session ended (memberRequest made this a guest): the page shows its login notice.
        setPhase("idle");
        setValues(EMPTY);
        onClose();
        return;
      }
      const mapped = isApiError(caught) ? passwordFieldError(caught.code) : null;
      setFieldError(mapped);
      setPhase(mapped ? "idle" : "failed");
    }
  };

  return (
    <Dialog
      open={open}
      onClose={close}
      title="비밀번호 변경"
      layout="responsive"
      width={480}
      sheetInset
      scrollArea
      closeDisabled={saving}
    >
      <form ref={form} onSubmit={submit} noValidate aria-busy={saving || undefined} className="flex min-h-0 flex-1 flex-col gap-4">
        {/* 6px inner margin: the 3px focus outline (2px offset) is not cut by the scroll edge. */}
        <div className="-m-1.5 flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-1.5">
          <p className="text-small text-fg-secondary">{PASSWORD_HINT}</p>
          {FIELDS.map((field) => (
            <Field
              key={field.name}
              label={field.label}
              type="password"
              name={field.name}
              autoComplete={field.autoComplete}
              placeholder={field.placeholder}
              maxLength={128}
              value={values[field.name]}
              disabled={saving}
              error={fieldError?.field === field.name ? fieldError.message : null}
              onChange={(event) => {
                const value = event.target.value;
                setValues((current) => ({ ...current, [field.name]: value }));
                if (fieldError?.field === field.name) setFieldError(null);
              }}
            />
          ))}
        </div>
        {saving && (
          <p role="status" className="text-small text-fg-secondary">
            비밀번호를 변경하고 있습니다.
          </p>
        )}
        {phase === "failed" && (
          <p role="alert" className="text-small text-error">
            {PASSWORD_FAILED_TEXT}
          </p>
        )}
        <div className="grid grid-cols-2 gap-2">
          <Button variant="secondary" disabled={saving} onClick={close}>
            취소
          </Button>
          <Button type="submit" variant="primary" disabled={saving || !filled}>
            {saving ? "변경 중…" : phase === "failed" ? "다시 시도" : "비밀번호 변경"}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
