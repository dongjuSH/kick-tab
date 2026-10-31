import Link from "next/link";
import type { ButtonHTMLAttributes, ComponentProps, ReactNode } from "react";
import { cx } from "./cx";
import { Icon, type IconName } from "./Icon";

/** Figma 55:27: primary / secondary / ghost. */
export type ButtonVariant = "primary" | "secondary" | "ghost";

const BASE =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-control px-4 text-body font-medium " +
  "transition-colors disabled:cursor-not-allowed disabled:border-transparent " +
  "disabled:bg-action-disabled disabled:text-fg-muted aria-disabled:cursor-not-allowed";

const VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-action text-fg-inverse hover:bg-action-hover",
  secondary: "border border-line-strong bg-surface text-fg hover:bg-subtle",
  ghost: "text-fg hover:bg-subtle",
};

export function buttonClass(variant: ButtonVariant = "secondary", fullWidth = false, className?: string) {
  return cx(BASE, VARIANTS[variant], fullWidth && "w-full", className);
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
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
