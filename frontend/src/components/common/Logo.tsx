import Image from "next/image";

/**
 * Approved header logo (symbol + outlined wordmark, logo-header.svg). Figma 49:58 shows it
 * in a 46px slot on desktop and 49:571 in a 40px slot on mobile; the width keeps its ratio.
 */
const SIZES = { header: 46, "header-mobile": 40 } as const;
const RATIO = 154.16666666666666 / 36;

export function Logo({ size }: { size: keyof typeof SIZES }) {
  const height = SIZES[size];
  const width = height * RATIO;
  return (
    <span className="inline-flex items-center">
      <Image
        src="/brand/logo-header.svg"
        alt="KickTab"
        width={Math.round(width)}
        height={height}
        style={{ width, height }}
        unoptimized
        loading="eager"
      />
    </span>
  );
}
