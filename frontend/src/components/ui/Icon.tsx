import Image from "next/image";

/** SVG icons exported from Figma into public/icons/. */
export type IconName =
  | "chevron-down"
  | "chevron-left"
  | "chevron-right"
  | "menu"
  | "x"
  | "search"
  | "info"
  | "thumbs";

const NATURAL_SIZE: Record<IconName, number> = {
  "chevron-down": 16,
  "chevron-left": 18,
  "chevron-right": 18,
  menu: 18,
  x: 18,
  search: 24,
  info: 24,
  thumbs: 16,
};

interface IconProps {
  name: IconName;
  size?: number;
  className?: string;
}

/** Decorative icon. Give the surrounding button an aria-label when it has no text. */
export function Icon({ name, size = NATURAL_SIZE[name], className }: IconProps) {
  return (
    <Image
      src={`/icons/${name}.svg`}
      width={size}
      height={size}
      alt=""
      aria-hidden
      unoptimized
      className={className}
    />
  );
}
