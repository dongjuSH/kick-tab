import Link from "next/link";
import { Suspense } from "react";
import { Logo } from "@/components/common/Logo";
import { Top5Strip, Top5StripFallback } from "@/features/top5/Top5Strip";
import { HeaderAuth } from "./HeaderAuth";
import { HeaderHeight } from "./HeaderHeight";
import { MainNav, MainNavFallback } from "./MainNav";
import { MobileMenu } from "./MobileMenu";

/**
 * Global header + TOP 5 strip, fixed together at the top while scrolling (COM-003).
 * Figma 49:58 (desktop, 86 + 1 + 56 + 1 = 144px) / 49:571 (mobile, 68 + 1 + 84 + 1 = 154px). Parts that read the current path
 * sit in Suspense so pages with a runtime param (`/matches/[id]`) keep a prerendered shell.
 */
export function SiteHeader() {
  return (
    <header className="sticky top-0 z-30 bg-surface">
      <HeaderHeight />
      <a
        href="#main"
        className="sr-only z-50 rounded-control bg-surface px-4 py-2 focus:not-sr-only focus:absolute focus:left-4 focus:top-2"
      >
        본문으로 건너뛰기
      </a>
      <div className="border-b border-line">
        <div className="kt-container flex items-center py-3 lg:py-5">
          <Link href="/" aria-label="KickTab 홈" className="shrink-0 rounded-control lg:mr-4">
            <span className="hidden lg:flex">
              <Logo size="header" />
            </span>
            <span className="flex lg:hidden">
              <Logo size="header-mobile" />
            </span>
          </Link>
          <div className="hidden lg:block">
            <Suspense fallback={<MainNavFallback />}>
              <MainNav />
            </Suspense>
          </div>
          <div className="flex-1" />
          <div className="hidden lg:block">
            <HeaderAuth layout="desktop" />
          </div>
          <div className="lg:hidden">
            <Suspense fallback={<span className="block size-11" />}>
              <MobileMenu />
            </Suspense>
          </div>
        </div>
      </div>
      <Suspense fallback={<Top5StripFallback />}>
        <Top5Strip />
      </Suspense>
    </header>
  );
}
