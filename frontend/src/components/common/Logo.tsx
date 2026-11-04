import Image from "next/image";
import { cx } from "@/components/ui/cx";

/** Approved brand exports include the outlined wordmark and their own slot geometry. */
const SIZES = {
  header: { height: 36, file: "logo-header.svg" },
  "header-mobile": { height: 32, file: "logo-mobile.svg" },
  footer: { height: 24, file: "logo-footer.svg" },
} as const;

export function Logo({ size, className }: { size: keyof typeof SIZES; className?: string }) {
  const { height, file } = SIZES[size];
  const width = (height * 154.16666666666666) / 36;
  return (
    <span className={cx("inline-flex items-center", className)}>
      <Image
        src={`/brand/${file}`}
        alt="KickTab"
        width={Math.round(width)}
        height={height}
        style={{ width, height }}
        unoptimized
        loading={size === "footer" ? "lazy" : "eager"}
      />
    </span>
  );
}
