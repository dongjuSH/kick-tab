import Image from "next/image";

/** SVG icons exported from Figma into public/icons/. */
export type IconName = "chevron-down" | "chevron-right" | "menu" | "x" | "search";

const NATURAL_SIZE: Record<IconName, number> = {
  "chevron-down": 16,
  "chevron-right": 16,
  menu: 18,
  x: 18,
  search: 24,
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
