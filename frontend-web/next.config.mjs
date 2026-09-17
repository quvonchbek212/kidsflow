/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  experimental: {
    // Sahifalar `force-dynamic` (CSP nonce sababli). Next 15'da dinamik
    // segmentlarning router keshi sukut bo'yicha 0 soniya — ya'ni oldindan
    // yuklangan yuk darhol eskiradi va bosilganda yana serverga borilardi.
    // 60 soniya bir sessiya ichida bo'limlar orasida tez o'tish uchun yetarli;
    // ma'lumot baribir brauzerda API'dan qayta so'raladi, shuning uchun eskirgan
    // raqam ko'rinib qolmaydi.
    staleTimes: { dynamic: 60, static: 180 },
  },
};

export default nextConfig;
