"use client";

import Image from "next/image";
import { useState } from "react";
import { cx } from "@/components/ui/cx";

const PLACEHOLDER_IMAGE = "/placeholder.svg";

interface RemoteImageProps {
  src: string | null | undefined;
  /** Name used for alt text, e.g. the team or player name. */
  name: string;
  size?: number;
  className?: string;
}

/**
 * Image from the API (only rights-approved URLs are sent, guide §6.5). Falls back to the
 * common placeholder (Figma 55:26) when the URL is null or fails to load.
 */
function RemoteImage({ src, name, size = 20, className, rounded }: RemoteImageProps & { rounded: boolean }) {
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  const usable = src && src !== failedSrc ? src : null;
  return (
    <Image
      src={usable ?? PLACEHOLDER_IMAGE}
      alt={usable ? name : ""}
      width={size}
      height={size}
      // External crests/photos are served as-is; no optimisation proxy.
      unoptimized
      onError={() => setFailedSrc(src ?? null)}
      // Fixed box: the global img reset (height: auto) would otherwise warn and reflow.
      style={{ width: size, height: size }}
      className={cx("shrink-0 object-contain", rounded && "rounded-full object-cover", className)}
    />
  );
}

/** Team or competition emblem. */
export function TeamCrest(props: RemoteImageProps) {
  return <RemoteImage {...props} rounded={false} />;
}

/** Player photo (round). */
export function PlayerPhoto(props: RemoteImageProps) {
  return <RemoteImage {...props} rounded />;
}
