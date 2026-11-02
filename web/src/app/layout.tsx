import type { Metadata } from "next";
import "./globals.css";
import { TopNav } from "@/components/layout/top-nav";
import { Footer } from "@/components/layout/footer";

export const metadata: Metadata = {
  title: "GridLens · National Electricity Grid Analytics Data Warehouse",
  description:
    "Academic BI and OLAP analytics dashboard for the National Electricity Grid of Sri Lanka. University of Ruhuna, Faculty of Technology, Department of ICT.",
  keywords: [
    "GridLens",
    "Sri Lanka Electricity",
    "CEB",
    "PUCSL",
    "NASA POWER",
    "Data Warehouse",
    "PostgreSQL 18",
    "Next.js",
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full antialiased light">
      <body className="min-h-full flex flex-col bg-[#F8F9FB] text-[#19222D]">
        <TopNav isLive={true} />
        <main className="flex-1 max-w-[1500px] w-full mx-auto px-4 md:px-9 py-8 md:py-10">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}
