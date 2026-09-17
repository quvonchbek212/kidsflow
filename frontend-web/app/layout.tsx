import { Bricolage_Grotesque, Inter, JetBrains_Mono } from "next/font/google";
import type { Metadata, Viewport } from "next";
import { headers } from "next/headers";
import type { ReactNode } from "react";

import { AppChrome } from "@/components/AppChrome";
import { ModalProvider } from "@/components/ui/ModalProvider";
import { ToastProvider } from "@/components/ui/ToastProvider";

import "./globals.css";
import "./app-shell.css";

const bricolage = Bricolage_Grotesque({
  subsets: ["latin"],
  weight: ["600", "700"],
  variable: "--font-display",
  display: "swap",
});
const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-body",
  display: "swap",
});
const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono",
  display: "swap",
});

// CSP nonce har bir so'rovda yangi bo'lishi kerak, statik prerender qilingan
// HTML esa qotib qolgan nonce bilan keladi — shuning uchun sahifalar dinamik
// render qilinadi. Bu ilovadagi barcha sahifalar login talab qiladi va
// brauzerda chiziladi, ya'ni statik prerenderdan yutuq deyarli yo'q edi.
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "KIDSFLOW",
  description: "Xususiy bog'chalar uchun boshqaruv platformasi",
  // Ilova login talab qiladi va tashqariga ulashilmaydi, shuning uchun
  // ijtimoiy tarmoq (OG) rasmi qo'shilmadi — faqat brauzer/telefon ikonkalari.
  applicationName: "KIDSFLOW",
};

// Android manzil paneli va iOS holat paneli brend rangiga bo'yaladi. Ikkala
// mavzu uchun alohida: tungi rejimda ochroq ko'k qorong'i panelga mos tushadi.
export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#1668b8" },
    { media: "(prefers-color-scheme: dark)", color: "#171b23" },
  ],
};

/* Mavzu birinchi chizilishdan OLDIN qo'yilishi kerak. Ilgari u AppShell'dagi
   `useEffect` ichida edi — ya'ni sahifa avval yorug' chizilib, keyin tungiga
   o'tardi va tungi rejim tanlagan foydalanuvchi har safar oq chaqnashni
   ko'rardi. Bu skript `<head>` da bloklab ishlaydi, shuning uchun chaqnash
   yo'q. Saqlangan tanlov bo'lmasa OS sozlamasi olinadi (ilgari umuman
   qaralmasdi). localStorage maxfiy rejimda istisno tashlashi mumkin —
   shuning uchun try/catch. */
const THEME_INIT = `try{var s=localStorage.getItem('kidsflow_theme');var d=s==='dark'||(s!=='light'&&matchMedia('(prefers-color-scheme: dark)').matches);document.documentElement.setAttribute('data-theme',d?'dark':'light')}catch(e){}`;

export default async function RootLayout({
  children,
}: {
  children: ReactNode;
}): Promise<ReactNode> {
  // CSP `script-src` nonce talab qiladi ('unsafe-inline' yo'q) — middleware
  // uni har so'rovda `x-nonce` sarlavhasiga qo'yadi.
  const nonce = (await headers()).get("x-nonce") ?? undefined;

  return (
    // `data-theme` ni yuqoridagi skript hidratatsiyadan oldin qo'yadi, ya'ni
    // serverdagi HTML bilan mos kelmaydi — bu ataylab shunday. Ogohlantirish
    // faqat shu elementning atributlariga taalluqli, ichkarisiga emas.
    <html
      lang="uz"
      suppressHydrationWarning
      className={`${bricolage.variable} ${inter.variable} ${jetbrainsMono.variable}`}
    >
      <head>
        {/* Saytda o'z tungi rejimi bor. Dark Reader kengaytmasi ranglarni
            ikkinchi marta o'zgartirib dizaynni buzardi va ikonkalarga
            atribut yozib hidratatsiya ogohlantirishini chiqarardi. */}
        <meta name="darkreader-lock" />
        {/* Brauzer xavfsizlik uchun `nonce` atributini DOM'dan yashiradi,
            shuning uchun u serverdagi HTML bilan mos kelmaydi — bu normal. */}
        <script
          nonce={nonce}
          suppressHydrationWarning
          dangerouslySetInnerHTML={{ __html: THEME_INIT }}
        />
      </head>
      <body>
        <ToastProvider>
          <ModalProvider>
            {/* Qobiq layout darajasida — marshrut almashganda u saqlanadi,
                faqat kontent yangilanadi. */}
            <AppChrome>{children}</AppChrome>
          </ModalProvider>
        </ToastProvider>
      </body>
    </html>
  );
}
