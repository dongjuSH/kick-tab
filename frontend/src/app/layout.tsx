import type { Metadata } from "next";
import { Inter, Noto_Sans_KR } from "next/font/google";
import { MobileBottomBar } from "@/components/layout/MobileBottomBar";
import { SiteFooter } from "@/components/layout/SiteFooter";
import { SiteHeader } from "@/components/layout/SiteHeader";
import { FeedbackProvider } from "@/features/feedback/FeedbackProvider";
import { Providers } from "./providers";
import "./globals.css";

const notoSansKr = Noto_Sans_KR({
  variable: "--font-noto-sans-kr",
  weight: ["400", "500", "700"],
  subsets: ["latin"],
  display: "swap",
});

// Wordmark only (Figma logo uses Inter Bold).
const inter = Inter({
  variable: "--font-inter",
  weight: ["700"],
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "KickTab - 해외 축구의 모든 순간, 한 탭에서",
    template: "%s | KickTab",
  },
  description: "해외 축구 경기 일정·결과·순위·뉴스를 한 곳에서 확인하세요.",
  applicationName: "KickTab",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ko" className={`${notoSansKr.variable} ${inter.variable} h-full`}>
      <body className="flex min-h-full flex-col">
        <Providers>
          <FeedbackProvider>
            <SiteHeader />
            <main id="main" className="flex flex-1 flex-col">
              {children}
            </main>
            <SiteFooter />
            <MobileBottomBar />
          </FeedbackProvider>
        </Providers>
      </body>
    </html>
  );
}
