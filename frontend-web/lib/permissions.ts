// Rol asosidagi UI ruxsatlari (skelet).
// MUHIM: frontenddagi yashirish xavfsizlik emas — ruxsatlar doimo backendda
// tekshiriladi (loyiha strukturasi, 2.3-bo'lim).

export type Role = "OWNER" | "MANAGER" | "TEACHER" | "PARENT";

export function canViewFinance(role: Role): boolean {
  return role === "OWNER" || role === "MANAGER";
}
