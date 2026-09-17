import { NextResponse, type NextRequest } from "next/server";

/**
 * Content-Security-Policy — har bir so'rovga yangi nonce bilan.
 *
 * Nega nonce, `'unsafe-inline'` emas: CSP ning asosiy maqsadi kiritilgan
 * skriptni ishga tushishdan to'xtatish. `script-src 'unsafe-inline'` yozilsa
 * aynan shu himoya yo'qoladi va sarlavha deyarli bezakka aylanadi. Next.js
 * o'zining ichki skriptlarini shu nonce bilan belgilaydi (u `x-nonce`
 * sarlavhasini o'qiydi), shuning uchun ular ishlaydi, begonasi esa yo'q.
 *
 * `style-src` da `'unsafe-inline'` qoldirilgan: Next.js va sahifalardagi
 * `style={{…}}` inline uslub yozadi, uslub kiritish esa skript kiritishdan
 * ancha kam xavfli.
 *
 * Bu ilovadagi barcha sahifalar login talab qiladi va brauzerda chiziladi,
 * shuning uchun nonce sababli statik prerender o'rniga dinamik render
 * bo'lishi sezilarli yo'qotish emas.
 */
export function middleware(request: NextRequest): NextResponse {
  const nonce = Buffer.from(crypto.randomUUID()).toString("base64");

  // Backend boshqa domenda bo'lsa (lokalda :8000) `connect-src` ga qo'shiladi.
  // Productionda API `/api/v1` — o'sha domenning o'zi, ya'ni 'self' yetarli.
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
  let apiOrigin = "";
  try {
    apiOrigin = apiBase.startsWith("http") ? new URL(apiBase).origin : "";
  } catch {
    apiOrigin = "";
  }

  // `next dev` modullarni `eval()` orqali yuklaydi (webpack `eval-source-map`),
  // shuning uchun faqat development'da `'unsafe-eval'` kerak bo'ladi. Usiz
  // butun client JS bloklanadi va sahifa jonlanmaydi (hydration bo'lmaydi).
  // Production build'da `eval` ishlatilmaydi — u yerda bu yumshatish yo'q.
  const devEval =
    process.env.NODE_ENV === "development" ? " 'unsafe-eval'" : "";

  // `upgrade-insecure-requests` brauzerga barcha `http://` so'rovlarni
  // `https://` ga o'tkazishni buyuradi. Productionda bu to'g'ri — u yerda sayt
  // TLS orqali beriladi. Developmentda esa hech qanday foyda bermaydi va
  // `localhost` dan tashqari har qanday manzilni butunlay ishdan chiqaradi:
  // brauzerlar `localhost` ni "ishonchli manba" deb bu qoidadan ozod qiladi,
  // LAN manzilini (masalan telefondan `http://192.168.x.x:3000`) esa yo'q —
  // natijada CSS va JS `https://192.168.x.x:3000` ga ketib
  // `ERR_SSL_PROTOCOL_ERROR` bilan yiqiladi va sahifa umuman jonlanmaydi.
  // Shuning uchun u faqat productionda qo'shiladi.
  const upgradeInsecure =
    process.env.NODE_ENV === "development" ? [] : ["upgrade-insecure-requests"];

  const csp = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${devEval}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self'",
    `connect-src 'self'${apiOrigin ? ` ${apiOrigin}` : ""}`,
    // Ilova hech qanday plagin, applet yoki begona freym ishlatmaydi.
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    // X-Frame-Options ning zamonaviy muqobili — clickjackingga qarshi.
    "frame-ancestors 'none'",
    ...upgradeInsecure,
  ].join("; ");

  // Next.js nonce'ni SO'ROV sarlavhasidagi CSP dan o'qiydi va o'z script
  // teglariga qo'yadi. Faqat javob sarlavhasi qo'yilsa teglar nonce'siz
  // qoladi va `strict-dynamic` ularning hammasini bloklaydi — ya'ni sayt
  // butunlay ishlamay qoladi. Shu sababli ikkalasiga ham yoziladi.
  const headers = new Headers(request.headers);
  headers.set("x-nonce", nonce);
  headers.set("Content-Security-Policy", csp);

  const response = NextResponse.next({ request: { headers } });
  response.headers.set("Content-Security-Policy", csp);
  return response;
}

export const config = {
  matcher: [
    // Statik fayllar va rasm optimizatsiyasi bundan chetda: ular HTML emas,
    // ularga CSP qo'yishning ma'nosi yo'q va har so'rovda nonce hisoblash
    // keraksiz yuk beradi.
    {
      source: "/((?!_next/static|_next/image|favicon.ico).*)",
      missing: [
        { type: "header", key: "next-router-prefetch" },
        { type: "header", key: "purpose", value: "prefetch" },
      ],
    },
  ],
};
