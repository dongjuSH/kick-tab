import type { SVGProps } from "react";
import type { EventKind } from "./model";

/**
 * Match detail icons drawn inline as vectors so they stay sharp at their real size
 * (MAT-002: blurry or broken-looking icons are replaced). All are decorative: the text next
 * to them says the same thing.
 */
type Props = SVGProps<SVGSVGElement> & { size?: number };

function Svg({ size = 16, children, ...props }: Props) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      aria-hidden
      focusable="false"
      shapeRendering="geometricPrecision"
      {...props}
    >
      {children}
    </svg>
  );
}

const STROKE = { stroke: "currentColor", strokeWidth: 1.5, strokeLinecap: "round", strokeLinejoin: "round" } as const;

function Ball(props: Props) {
  return (
    <Svg {...props}>
      <circle cx="8" cy="8" r="6.25" {...STROKE} />
      <path d="M8 5.2 10.6 7.1 9.6 10.1H6.4L5.4 7.1Z" fill="currentColor" />
      <path d="M8 5.2V1.9M10.6 7.1l3.1-1M9.6 10.1l1.9 2.7M6.4 10.1l-1.9 2.7M5.4 7.1l-3.1-1" {...STROKE} strokeWidth={1.2} />
    </Svg>
  );
}

function Swap(props: Props) {
  return (
    <Svg {...props}>
      <path d="M2.5 5.5h10M10 3l2.5 2.5L10 8M13.5 10.5h-10M6 8l-2.5 2.5L6 13" {...STROKE} />
    </Svg>
  );
}

function Card({ fill, ...props }: Props & { fill: string }) {
  return (
    <Svg {...props}>
      <rect x="4.25" y="2" width="7.5" height="12" rx="1.25" fill={fill} />
    </Svg>
  );
}

function Cancelled(props: Props) {
  return (
    <Svg {...props}>
      <circle cx="8" cy="8" r="6.25" {...STROKE} />
      <path d="M3.6 12.4 12.4 3.6" {...STROKE} />
    </Svg>
  );
}

function Missed(props: Props) {
  return (
    <Svg {...props}>
      <circle cx="8" cy="8" r="6.25" {...STROKE} />
      <path d="M5.75 5.75l4.5 4.5M10.25 5.75l-4.5 4.5" {...STROKE} />
    </Svg>
  );
}

function Screen(props: Props) {
  return (
    <Svg {...props}>
      <rect x="1.75" y="3" width="12.5" height="8.5" rx="1.25" {...STROKE} />
      <path d="M6 14h4M8 11.5V14" {...STROKE} />
    </Svg>
  );
}

function Dot(props: Props) {
  return (
    <Svg {...props}>
      <circle cx="8" cy="8" r="2.5" fill="currentColor" />
    </Svg>
  );
}

// Card colours follow the Figma timeline (52:151): yellow and red cards as filled shapes.
const YELLOW = "#EAB308";
const RED = "#DC2626";

/** One icon per timeline record kind (goal, substitution, yellow/red card, cancelled goal). */
export function EventIcon({ kind }: { kind: EventKind }) {
  switch (kind) {
    case "goal":
      return <Ball className="text-fg" />;
    case "missed":
      return <Missed className="text-fg-muted" />;
    case "subst":
      return <Swap className="text-action" />;
    case "yellow":
      return <Card fill={YELLOW} />;
    case "red":
      return <Card fill={RED} />;
    case "cancelled":
      return <Cancelled className="text-error" />;
    case "var":
      return <Screen className="text-fg-secondary" />;
    default:
      return <Dot className="text-fg-muted" />;
  }
}

export function ThumbIcon({ down = false }: { down?: boolean }) {
  // Down is the up shape mirrored vertically only, so the thumb stays on the same side.
  return (
    <Svg className="text-fg-secondary" style={down ? { transform: "scaleY(-1)" } : undefined}>
      <path
        d="M4.75 7v6.75M4.75 7H2.25v6.75h2.5M4.75 7 7.9 2.4c.6-.6 1.85 0 1.85 1.25V6.1h2.6c1.2 0 1.85.65 1.3 1.85l-1.3 4.6c-.15.65-.65 1.2-1.3 1.2h-6.3"
        {...STROKE}
      />
    </Svg>
  );
}

export function NoticeIcon() {
  return (
    <Svg size={20} viewBox="0 0 20 20">
      <circle cx="10" cy="10" r="7.75" {...STROKE} />
      <path d="M10 6.25v4.5" {...STROKE} strokeWidth={1.75} />
      <circle cx="10" cy="13.6" r="1" fill="currentColor" />
    </Svg>
  );
}
