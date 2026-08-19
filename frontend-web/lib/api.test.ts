import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

/**
 * Token yangilash mantiqi — ilovadagi eng nozik joy va shu paytgacha umuman
 * qoplanmagan edi. Bu yerda tekshiriladi:
 *
 * - 401 kelganda so'rov bir marta (va faqat bir marta) qaytariladi;
 * - bir vaqtda ketayotgan bir nechta 401 bitta yangilashga birlashadi
 *   (backend refresh tokenni rotation qiladi — ikkinchi yangilash eskirgan
 *   token bilan ketib, foydalanuvchini tizimdan chiqarib yuborardi);
 * - yangilash muvaffaqiyatsiz bo'lsa tokenlar tozalanadi;
 * - tokensiz so'rovlarda (login) 401 backend xabarini saqlab qoladi.
 */

const store = new Map<string, string>();

// Stublash har bir testdan oldin qayta bajariladi: `unstubAllGlobals()`
// afterEach'da ularni olib tashlaydi, modul darajasida bir marta qo'yilsa
// ikkinchi testdan boshlab localStorage yo'qolib qolardi.
function stubStorage(): void {
  const storage = {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => void store.set(k, v),
    removeItem: (k: string) => void store.delete(k),
    clear: () => store.clear(),
  };
  vi.stubGlobal("localStorage", storage);
  vi.stubGlobal("window", { localStorage: storage });
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

let api: typeof import("./api").api;
let ApiError: typeof import("./api").ApiError;
let setTokens: typeof import("./auth").setTokens;
let getToken: typeof import("./auth").getToken;

beforeEach(async () => {
  store.clear();
  stubStorage();
  vi.resetModules();
  const apiModule = await import("./api");
  const authModule = await import("./auth");
  api = apiModule.api;
  ApiError = apiModule.ApiError;
  setTokens = authModule.setTokens;
  getToken = authModule.getToken;
  setTokens({ accessToken: "eski-access", refreshToken: "eski-refresh" });
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("401 dan keyin token yangilash", () => {
  it("yangilangach so'rovni bir marta qaytaradi", async () => {
    const calls: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        calls.push(String(url));
        if (String(url).endsWith("/auth/refresh")) {
          return jsonResponse(200, {
            access_token: "yangi-access",
            refresh_token: "yangi-refresh",
          });
        }
        // Birinchi urinish 401, yangilangandan keyin 200.
        return calls.filter((c) => c.endsWith("/branches")).length === 1
          ? jsonResponse(401, { detail: "muddati o'tgan" })
          : jsonResponse(200, []);
      }),
    );

    await expect(api.listBranches()).resolves.toEqual([]);
    expect(calls.filter((c) => c.endsWith("/auth/refresh"))).toHaveLength(1);
    expect(calls.filter((c) => c.endsWith("/branches"))).toHaveLength(2);
    expect(getToken()).toBe("yangi-access");
  });

  it("bir vaqtda kelgan bir nechta 401 bitta yangilashga birlashadi", async () => {
    // Bu eng muhim tekshiruv: refresh token rotation qilinadi, ya'ni
    // ikkinchi yangilash eskirgan token bilan ketsa 401 olib, foydalanuvchini
    // tizimdan chiqarib yuborardi.
    let refreshCount = 0;
    const seen = new Map<string, number>();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        const u = String(url);
        if (u.endsWith("/auth/refresh")) {
          refreshCount += 1;
          await new Promise((r) => setTimeout(r, 10));
          return jsonResponse(200, {
            access_token: "yangi-access",
            refresh_token: "yangi-refresh",
          });
        }
        const n = (seen.get(u) ?? 0) + 1;
        seen.set(u, n);
        return n === 1 ? jsonResponse(401, {}) : jsonResponse(200, []);
      }),
    );

    await Promise.all([
      api.listBranches(),
      api.listGroups(),
      api.listChildren(),
    ]);

    expect(refreshCount).toBe(1);
  });

  it("yangilash muvaffaqiyatsiz bo'lsa tokenlarni tozalaydi", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) =>
        String(url).endsWith("/auth/refresh")
          ? jsonResponse(401, {})
          : jsonResponse(401, {}),
      ),
    );

    await expect(api.listBranches()).rejects.toBeInstanceOf(ApiError);
    expect(getToken()).toBeNull();
  });

  it("refresh token bo'lmasa umuman urinmaydi", async () => {
    store.clear();
    const fetchMock = vi.fn(async (url: string) => {
      void url;
      return jsonResponse(401, {});
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.listBranches()).rejects.toBeInstanceOf(ApiError);
    const urls = fetchMock.mock.calls.map((c) => String(c[0]));
    expect(urls.filter((u) => u.endsWith("/auth/refresh"))).toHaveLength(0);
  });
});

describe("tokensiz so'rovlar", () => {
  it("login 401'ida backend xabarini saqlaydi", async () => {
    // "Avtorizatsiya talab qilinadi." bilan almashtirilsa, foydalanuvchi
    // parolni noto'g'ri yozganini bilmay qolardi.
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse(401, { detail: "Login yoki parol noto'g'ri." }),
      ),
    );

    await expect(api.login("+998901112233", "xato")).rejects.toThrow(
      "Login yoki parol noto'g'ri.",
    );
  });
});
