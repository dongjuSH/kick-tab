import Link from "next/link";
import type { ButtonHTMLAttributes, ComponentProps, ReactNode } from "react";
import { cx } from "./cx";
import { Icon, type IconName } from "./Icon";

/**
 * Figma `KickTab/Button · 4종 × 5상태` (691:8003 in 55:27, 2026-11-24):
 * - primary: the main action.
 * - secondary: retry / reset / more / cancel / add / keep browsing.
 * - text: in-row remove · delete · edit, account "회원 탈퇴".
 * - danger: the button that actually deletes or withdraws.
 * Dialogs put cancel (secondary) on the left and the action (primary, or danger) on the right.
 */
export type ButtonVariant = "primary" | "secondary" | "text" | "danger";

// 44px target, 8px radius, 14px Medium. Keyboard focus is the global 3px :focus-visible
// outline. Hover/pressed only apply while enabled; pressed is :active.
const BASE =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-control px-4 text-body font-medium " +
  "transition-colors disabled:cursor-not-allowed disabled:text-fg-disabled aria-disabled:cursor-not-allowed";

const VARIANTS: Record<ButtonVariant, string> = {
  primary:
    "bg-action text-fg-inverse disabled:bg-subtle " +
    "not-disabled:hover:bg-action-hover not-disabled:active:bg-action-hover not-disabled:active:kt-press-12",
  secondary:
    "border border-line-strong bg-surface text-fg-secondary disabled:border-line disabled:bg-subtle " +
    "not-disabled:hover:bg-canvas not-disabled:active:bg-subtle",
  text: "text-fg-secondary not-disabled:hover:bg-subtle not-disabled:active:bg-line",
  danger:
    "bg-error text-fg-inverse disabled:bg-subtle " +
    "not-disabled:hover:kt-press-8 not-disabled:active:kt-press-18",
};

export function buttonClass(variant: ButtonVariant = "secondary", fullWidth = false, className?: string) {
  return cx(BASE, VARIANTS[variant], fullWidth && "w-full", className);
}

interface ButtonProps extends ComponentProps<"button"> {
  variant?: ButtonVariant;
  fullWidth?: boolean;
}

export function Button({ variant = "secondary", fullWidth, className, type = "button", ...props }: ButtonProps) {
  return <button type={type} className={buttonClass(variant, fullWidth, className)} {...props} />;
}

interface ButtonLinkProps extends ComponentProps<typeof Link> {
  variant?: ButtonVariant;
  fullWidth?: boolean;
}

export function ButtonLink({ variant = "secondary", fullWidth, className, ...props }: ButtonLinkProps) {
  return <Link className={buttonClass(variant, fullWidth, className)} {...props} />;
}

interface IconButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> {
  icon: IconName;
  /** Required: icon-only buttons need an accessible name (guide §6.6). */
  label: string;
  children?: ReactNode;
}

/** 44×44 touch target with an 18px icon (Figma close/menu buttons). */
export function IconButton({ icon, label, className, type = "button", ...props }: IconButtonProps) {
  return (
    <button
      type={type}
      aria-label={label}
      className={cx(
        "inline-flex size-11 shrink-0 items-center justify-center rounded-control hover:bg-subtle",
        className,
      )}
      {...props}
    >
      <Icon name={icon} />
    </button>
  );
}
