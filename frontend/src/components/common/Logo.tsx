import Image from "next/image";
import { cx } from "@/components/ui/cx";

/**
 * KickTab logo: 80×48 symbol (Figma 55:22) + "KickTab" wordmark, 10px apart.
 * Heights: header desktop 36px, header mobile 32px, footer 24px (Figma 96:412).
 */
const SIZES = {
  header: { height: 36, text: "text-[23.4px] leading-[35px]" },
  "header-mobile": { height: 32, text: "text-[20.8px] leading-[31px]" },
  footer: { height: 24, text: "text-[15.6px] leading-[23.6px]" },
} as const;

export function Logo({ size, className }: { size: keyof typeof SIZES; className?: string }) {
  const { height, text } = SIZES[size];
  return (
    <span className={cx("inline-flex items-center gap-2.5", className)}>
      <Image
        src="/brand/symbol.svg"
        alt=""
        width={(height * 80) / 48}
        height={height}
        // Fixed box: preflight's height:auto would otherwise trigger an aspect-ratio warning.
        style={{ width: (height * 80) / 48, height }}
        unoptimized
        loading={size === "footer" ? "lazy" : "eager"}
      />
      <span className={cx("font-wordmark font-bold whitespace-nowrap", text)}>
        <span className="text-fg">Kick</span>
        <span className="text-action">Tab</span>
      </span>
    </span>
  );
}
