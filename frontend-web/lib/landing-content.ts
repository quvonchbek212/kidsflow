// Landing sahifa kontenti — o'zbek, rus, ingliz (8-bo'lim: uz/ru + en).

export type Lang = "uz" | "ru" | "en";

export interface Feature {
  icon: string;
  title: string;
  desc: string;
}

export interface Step {
  title: string;
  desc: string;
}

export interface LandingContent {
  nav: {
    features: string;
    advantages: string;
    how: string;
    privacy: string;
    login: string;
  };
  hero: {
    badge: string;
    title: string;
    subtitle: string;
    ctaPrimary: string;
    ctaSecondary: string;
  };
  mockup: { modules: string; realtime: string; realtimeSub: string; selfService: string; selfServiceSub: string };
  featuresTitle: string;
  featuresSubtitle: string;
  features: Feature[];
  advantagesTitle: string;
  advantagesSubtitle: string;
  advantages: Feature[];
  howTitle: string;
  howSubtitle: string;
  steps: Step[];
  ctaTitle: string;
  ctaSubtitle: string;
  ctaButton: string;
  footer: string;
}

export const CONTENT: Record<Lang, LandingContent> = {
  uz: {
    nav: {
      features: "Imkoniyatlar",
      advantages: "Afzalliklar",
      how: "Qanday ishlaydi",
      privacy: "Maxfiylik siyosati",
      login: "Tizimga kirish",
    },
    hero: {
      badge: "Xususiy bog'chalar uchun boshqaruv platformasi",
      title: "Bog'cha ishining barcha jarayonlarini birlashtiruvchi platforma",
      subtitle:
        "Davomatdan tortib to'lovlar va moliyaviy hisobotgacha — barcha jarayonlar yagona bog'langan tizimda. Tarbiyachi, ota-ona, menejer va egasi o'z ishini bir joyda bajaradi. O'zbek va rus tillarini hamda bir nechta filialni qo'llab-quvvatlaydi.",
      ctaPrimary: "Tizimga kirish",
      ctaSecondary: "Imkoniyatlar bilan tanishish",
    },
    mockup: {
      modules: "6+ modul va bo'lim",
      realtime: "Real-time",
      realtimeSub: "Telegram bildirishnomasi",
      selfService: "Ota-ona kabineti",
      selfServiceSub: "UZ / RU / EN",
    },
    featuresTitle: "Imkoniyatlar",
    featuresSubtitle: "Bog'chaning kundalik ishlarini avtomatlashtiradigan modullar.",
    features: [
      {
        icon: "📋",
        title: "Davomat va kunlik hisobot",
        desc: "Tarbiyachi bolalar davomatini belgilaydi, ovqat, uyqu va kayfiyat bo'yicha kunlik hisobot yuritadi.",
      },
      {
        icon: "💰",
        title: "To'lov va hisob-fakturalar",
        desc: "Oylik invoice, qo'lda to'lov, qarzdorlik, chegirma va reversal — moliyaviy yozuvlar o'chirilmaydi.",
      },
      {
        icon: "📊",
        title: "Moliyaviy dashboard",
        desc: "Real tushgan pul, hisoblangan daromad, xarajat va sof natija — filiallar bo'yicha aniq raqamlar.",
      },
      {
        icon: "🤖",
        title: "Telegram bot",
        desc: "Ota-onalar farzandining davomati, kunlik hisoboti va to'lovlarini Telegram orqali ko'radi.",
      },
      {
        icon: "✨",
        title: "AI yordamchi",
        desc: "Kunlik hisobot matni, chek OCR, ota-onalar uchun savol-javob va tarjima — faktlarga asoslangan.",
      },
      {
        icon: "🏢",
        title: "Filiallar va rollar",
        desc: "Bir nechta filial, OWNER / MANAGER / TEACHER / PARENT rollari va xavfsiz ma'lumot izolyatsiyasi.",
      },
    ],
    advantagesTitle: "Afzalliklar",
    advantagesSubtitle: "Nega KIDSFLOW bog'changiz uchun qulay.",
    advantages: [
      {
        icon: "⚡",
        title: "Qo'lda ishni kamaytiradi",
        desc: "Davomat, hisobot va to'lovlar avtomatlashtiriladi — daftar va Excel'ga hojat qolmaydi.",
      },
      {
        icon: "💬",
        title: "Ota-onalar bilan shaffof aloqa",
        desc: "Har bir hisobot va to'lov haqida ota-onaga avtomatik Telegram xabari boradi.",
      },
      {
        icon: "🔒",
        title: "Ma'lumotlar xavfsizligi",
        desc: "Tibbiy ma'lumotlar shifrlanadi, har bir amal audit jurnalida qoladi, ruxsatlar qat'iy tekshiriladi.",
      },
      {
        icon: "🎯",
        title: "Aniq moliyaviy nazorat",
        desc: "Egasi filiallar kesimida real pul, qarzdorlik va sof natijani bir ekranda ko'radi.",
      },
      {
        icon: "🌐",
        title: "Ko'p til va mobil",
        desc: "O'zbek va rus tillari, mobil ekranlar va tushunarli interfeys.",
      },
      {
        icon: "🧩",
        title: "Har bir bog'cha mustaqil",
        desc: "Har bir bog'cha alohida, izolyatsiyalangan tizimda ishlaydi — ma'lumotlar aralashmaydi.",
      },
    ],
    howTitle: "Qanday ishlaydi",
    howSubtitle: "To'rt oddiy qadamda ishga tushiring.",
    steps: [
      {
        title: "Sozlash",
        desc: "Bog'cha, birinchi filial va egasi hisobini yarating.",
      },
      {
        title: "Bola va ota-onani qo'shing",
        desc: "Bolani guruhga qabul qiling, ota-onaga bir martalik Telegram kodini bering.",
      },
      {
        title: "Kundalik ish",
        desc: "Davomat va kunlik hisobotni kiriting — ota-onalar avtomatik xabar oladi.",
      },
      {
        title: "Moliya va tahlil",
        desc: "Invoice, to'lov va xarajatlarni yuriting, dashboard orqali nazorat qiling.",
      },
    ],
    ctaTitle: "Bog'changizni bugundan raqamlashtiring",
    ctaSubtitle: "Tizimga kiring va bog'cha boshqaruvini bir joydan yuriting.",
    ctaButton: "Tizimga kirish",
    footer: "KIDSFLOW — xususiy bog'chalar uchun boshqaruv platformasi.",
  },

  ru: {
    nav: {
      features: "Возможности",
      advantages: "Преимущества",
      how: "Как работает",
      privacy: "Политика конфиденциальности",
      login: "Войти в систему",
    },
    hero: {
      badge: "Платформа управления частными детскими садами",
      title: "Платформа, объединяющая все процессы работы детского сада",
      subtitle:
        "От посещаемости до оплат и финансовых отчётов — все процессы в единой связанной системе. Воспитатель, родитель, менеджер и владелец работают в одном месте. Поддержка узбекского и русского языков и нескольких филиалов.",
      ctaPrimary: "Войти в систему",
      ctaSecondary: "Ознакомиться с возможностями",
    },
    mockup: {
      modules: "6+ модулей",
      realtime: "Real-time",
      realtimeSub: "Уведомления в Telegram",
      selfService: "Кабинет родителя",
      selfServiceSub: "UZ / RU / EN",
    },
    featuresTitle: "Возможности",
    featuresSubtitle: "Модули, автоматизирующие ежедневную работу сада.",
    features: [
      {
        icon: "📋",
        title: "Посещаемость и отчёты",
        desc: "Воспитатель отмечает посещаемость и ведёт ежедневный отчёт: питание, сон, настроение.",
      },
      {
        icon: "💰",
        title: "Оплаты и счета",
        desc: "Ежемесячные счета, ручная оплата, задолженность, скидки и реверс — записи не удаляются.",
      },
      {
        icon: "📊",
        title: "Финансовая панель",
        desc: "Реальные поступления, начисленный доход, расходы и чистый результат по филиалам.",
      },
      {
        icon: "🤖",
        title: "Telegram-бот",
        desc: "Родители видят посещаемость, отчёты и оплаты ребёнка через Telegram.",
      },
      {
        icon: "✨",
        title: "AI-помощник",
        desc: "Текст отчёта, OCR чеков, ответы для родителей и перевод — на основе фактов.",
      },
      {
        icon: "🏢",
        title: "Филиалы и роли",
        desc: "Несколько филиалов, роли OWNER / MANAGER / TEACHER / PARENT и изоляция данных.",
      },
    ],
    advantagesTitle: "Преимущества",
    advantagesSubtitle: "Почему KIDSFLOW удобен для вашего сада.",
    advantages: [
      {
        icon: "⚡",
        title: "Меньше ручной работы",
        desc: "Посещаемость, отчёты и оплаты автоматизированы — без тетрадей и Excel.",
      },
      {
        icon: "💬",
        title: "Прозрачная связь с родителями",
        desc: "О каждом отчёте и оплате родитель получает автоматическое уведомление в Telegram.",
      },
      {
        icon: "🔒",
        title: "Безопасность данных",
        desc: "Медицинские данные шифруются, каждое действие в журнале аудита, строгие права доступа.",
      },
      {
        icon: "🎯",
        title: "Точный финансовый контроль",
        desc: "Владелец видит поступления, задолженность и результат по филиалам на одном экране.",
      },
      {
        icon: "🌐",
        title: "Мультиязычность и мобильность",
        desc: "Узбекский и русский языки, мобильные экраны и понятный интерфейс.",
      },
      {
        icon: "🧩",
        title: "Каждый сад независим",
        desc: "Каждый сад работает в отдельной изолированной системе — данные не смешиваются.",
      },
    ],
    howTitle: "Как работает",
    howSubtitle: "Запуск в четыре простых шага.",
    steps: [
      { title: "Настройка", desc: "Создайте сад, первый филиал и аккаунт владельца." },
      {
        title: "Добавьте ребёнка и родителя",
        desc: "Зачислите ребёнка в группу, выдайте родителю одноразовый код Telegram.",
      },
      {
        title: "Ежедневная работа",
        desc: "Вносите посещаемость и отчёты — родители получают уведомления автоматически.",
      },
      {
        title: "Финансы и аналитика",
        desc: "Ведите счета, оплаты и расходы, контролируйте через панель.",
      },
    ],
    ctaTitle: "Оцифруйте свой сад уже сегодня",
    ctaSubtitle: "Войдите в систему и управляйте садом из одного места.",
    ctaButton: "Войти в систему",
    footer: "KIDSFLOW — платформа управления частными детскими садами.",
  },

  en: {
    nav: {
      features: "Features",
      advantages: "Advantages",
      how: "How it works",
      privacy: "Privacy policy",
      login: "Sign in",
    },
    hero: {
      badge: "Management platform for private kindergartens",
      title: "One platform that unifies every process of a kindergarten",
      subtitle:
        "From attendance to payments and financial reports — all processes in a single connected system. Teachers, parents, managers and owners work in one place. Supports Uzbek and Russian and multiple branches.",
      ctaPrimary: "Sign in",
      ctaSecondary: "Explore features",
    },
    mockup: {
      modules: "6+ modules",
      realtime: "Real-time",
      realtimeSub: "Telegram notifications",
      selfService: "Parent portal",
      selfServiceSub: "UZ / RU / EN",
    },
    featuresTitle: "Features",
    featuresSubtitle: "Modules that automate the daily work of a kindergarten.",
    features: [
      {
        icon: "📋",
        title: "Attendance & daily reports",
        desc: "Teachers mark attendance and keep a daily report of meals, nap and mood.",
      },
      {
        icon: "💰",
        title: "Payments & invoices",
        desc: "Monthly invoices, manual payments, debt, discounts and reversals — records are never deleted.",
      },
      {
        icon: "📊",
        title: "Financial dashboard",
        desc: "Cash collected, accrued revenue, expenses and net result — precise numbers per branch.",
      },
      {
        icon: "🤖",
        title: "Telegram bot",
        desc: "Parents see their child's attendance, reports and payments via Telegram.",
      },
      {
        icon: "✨",
        title: "AI assistant",
        desc: "Report text, receipt OCR, parent Q&A and translation — grounded in facts.",
      },
      {
        icon: "🏢",
        title: "Branches & roles",
        desc: "Multiple branches, OWNER / MANAGER / TEACHER / PARENT roles and strict data isolation.",
      },
    ],
    advantagesTitle: "Advantages",
    advantagesSubtitle: "Why KIDSFLOW fits your kindergarten.",
    advantages: [
      {
        icon: "⚡",
        title: "Less manual work",
        desc: "Attendance, reports and payments are automated — no more notebooks and Excel.",
      },
      {
        icon: "💬",
        title: "Transparent parent communication",
        desc: "Parents get an automatic Telegram message about every report and payment.",
      },
      {
        icon: "🔒",
        title: "Data security",
        desc: "Medical data is encrypted, every action is in the audit log, permissions are strictly checked.",
      },
      {
        icon: "🎯",
        title: "Precise financial control",
        desc: "The owner sees cash, debt and net result across branches on one screen.",
      },
      {
        icon: "🌐",
        title: "Multilingual & mobile",
        desc: "Uzbek and Russian, mobile-friendly screens and a clear interface.",
      },
      {
        icon: "🧩",
        title: "Each kindergarten is independent",
        desc: "Each kindergarten runs in its own isolated system — data never mixes.",
      },
    ],
    howTitle: "How it works",
    howSubtitle: "Get started in four simple steps.",
    steps: [
      { title: "Setup", desc: "Create the kindergarten, the first branch and the owner account." },
      {
        title: "Add a child and a parent",
        desc: "Enroll the child into a group, give the parent a one-time Telegram code.",
      },
      {
        title: "Daily work",
        desc: "Enter attendance and reports — parents are notified automatically.",
      },
      {
        title: "Finance & analytics",
        desc: "Manage invoices, payments and expenses, monitor via the dashboard.",
      },
    ],
    ctaTitle: "Digitize your kindergarten today",
    ctaSubtitle: "Sign in and run your kindergarten from a single place.",
    ctaButton: "Sign in",
    footer: "KIDSFLOW — management platform for private kindergartens.",
  },
};
