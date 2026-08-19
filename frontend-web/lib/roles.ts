/**
 * Foydalanuvchining amaldagi roli.
 *
 * Ma'lumotlar modeli bir foydalanuvchiga bir nechta rol berishga imkon beradi
 * (`user_role_assignments` alohida jadval, masalan "A filialda menejer,
 * B filialda tarbiyachi"). Interfeys esa bitta rolga qarab quriladi: yon panel
 * bandlari, ruxsat etilgan sahifalar va boshlang'ich manzil shundan olinadi.
 *
 * Ilgari `roles[0]` olinardi — ya'ni tanlov jadvaldan qaysi qator birinchi
 * kelishiga bog'liq edi. Bu ko'p rolli xodimda interfeysni tasodifiy ravishda
 * torroq qilib qo'yishi mumkin edi va xato bermasdi, shunchaki ba'zi bo'limlar
 * ko'rinmay qolardi.
 *
 * Endi eng keng huquqli rol tanlanadi. Bu xavfsiz: har bir so'rovni backend
 * baribir mustaqil tekshiradi, ya'ni interfeys keragidan ko'p ko'rsatib
 * qo'ysa ham ma'lumot oshkor bo'lmaydi — foydalanuvchi 403 oladi.
 *
 * Xodim yaratish API'si hozircha bitta rol qabul qiladi, shuning uchun
 * amalda ko'p rolli foydalanuvchi kam uchraydi; bu funksiya shu holat
 * paydo bo'lganda interfeys oldindan aytib bo'ladigan tarzda ishlashi uchun.
 */

// Kengdan torga. Ro'yxatda yo'q rol eng oxirida turadi.
const ROLE_RANK = ["OWNER", "MANAGER", "TEACHER", "PARENT"] as const;

export function primaryRole(
  roles: { role: string }[] | null | undefined,
): string {
  if (!roles || roles.length === 0) return "";
  let best = roles[0].role;
  let bestRank = rankOf(best);
  for (const { role } of roles) {
    const rank = rankOf(role);
    if (rank < bestRank) {
      best = role;
      bestRank = rank;
    }
  }
  return best;
}

function rankOf(role: string): number {
  const index = ROLE_RANK.indexOf(role as (typeof ROLE_RANK)[number]);
  return index === -1 ? ROLE_RANK.length : index;
}
