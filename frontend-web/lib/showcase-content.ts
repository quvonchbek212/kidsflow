// Rollar bo'yicha aylanuvchi (carousel) showcase kontenti — uz/ru/en.

import type { Lang } from "./landing-content";

export interface Slide {
  icon: string;
  tag: string;
  title: string;
  points: string[];
}

export interface ShowcaseContent {
  title: string;
  subtitle: string;
  slides: Slide[];
}

export const SHOWCASE: Record<Lang, ShowcaseContent> = {
  uz: {
    title: "Har bir rol uchun",
    subtitle: "Bir platforma — to'rt xil foydalanuvchi, har biriga mos ish o'rni.",
    slides: [
      {
        icon: "👑",
        tag: "Egasi",
        title: "Barcha filiallar moliyasi bir ekranda",
        points: [
          "Real tushgan pul va hisoblangan daromad",
          "Qarzdorlik va sof natija",
          "Filiallarni taqqoslash",
          "Audit jurnali va xavfsizlik",
        ],
      },
      {
        icon: "🧑‍💼",
        tag: "Menejer",
        title: "Kundalik operatsiyalar nazorati",
        points: [
          "Bolalar, vasiylar va guruhlar",
          "Invoice va qo'lda to'lov tasdiqlash",
          "Xarajatlar va qarzdorlar",
          "Telegram taklif kodlari",
        ],
      },
      {
        icon: "👩‍🏫",
        tag: "Tarbiyachi",
        title: "Davomat va hisobot bir necha bosishda",
        points: [
          "Tez davomat belgilash",
          "Kunlik hisobot: ovqat, uyqu, kayfiyat",
          "Foto va fayllar",
          "AI matn yordami (tasdiq bilan)",
        ],
      },
      {
        icon: "👨‍👩‍👧",
        tag: "Ota-ona",
        title: "Farzandingiz haqida real vaqtda",
        points: [
          "Davomat va kunlik hisobot",
          "To'lov holati va qarzdorlik",
          "Telegram orqali bildirishnoma",
          "AI yordamchiga savol berish",
        ],
      },
    ],
  },
  ru: {
    title: "Для каждой роли",
    subtitle: "Одна платформа — четыре типа пользователей, у каждого своё место.",
    slides: [
      {
        icon: "👑",
        tag: "Владелец",
        title: "Финансы всех филиалов на одном экране",
        points: [
          "Реальные поступления и начисленный доход",
          "Задолженность и чистый результат",
          "Сравнение филиалов",
          "Журнал аудита и безопасность",
        ],
      },
      {
        icon: "🧑‍💼",
        tag: "Менеджер",
        title: "Контроль ежедневных операций",
        points: [
          "Дети, опекуны и группы",
          "Счета и подтверждение оплат",
          "Расходы и должники",
          "Коды-приглашения Telegram",
        ],
      },
      {
        icon: "👩‍🏫",
        tag: "Воспитатель",
        title: "Посещаемость и отчёт в пару кликов",
        points: [
          "Быстрая отметка посещаемости",
          "Отчёт: питание, сон, настроение",
          "Фото и файлы",
          "Помощь AI с текстом (с подтверждением)",
        ],
      },
      {
        icon: "👨‍👩‍👧",
        tag: "Родитель",
        title: "О ребёнке в реальном времени",
        points: [
          "Посещаемость и ежедневный отчёт",
          "Статус оплат и задолженность",
          "Уведомления через Telegram",
          "Вопросы AI-помощнику",
        ],
      },
    ],
  },
  en: {
    title: "For every role",
    subtitle: "One platform — four kinds of users, each with the right workspace.",
    slides: [
      {
        icon: "👑",
        tag: "Owner",
        title: "All branch finances on one screen",
        points: [
          "Cash collected and accrued revenue",
          "Debt and net result",
          "Branch comparison",
          "Audit log and security",
        ],
      },
      {
        icon: "🧑‍💼",
        tag: "Manager",
        title: "Control of daily operations",
        points: [
          "Children, guardians and groups",
          "Invoices and payment confirmation",
          "Expenses and debtors",
          "Telegram invitation codes",
        ],
      },
      {
        icon: "👩‍🏫",
        tag: "Teacher",
        title: "Attendance and reports in a few clicks",
        points: [
          "Fast attendance marking",
          "Daily report: meals, nap, mood",
          "Photos and files",
          "AI text help (with approval)",
        ],
      },
      {
        icon: "👨‍👩‍👧",
        tag: "Parent",
        title: "Your child in real time",
        points: [
          "Attendance and daily report",
          "Payment status and debt",
          "Notifications via Telegram",
          "Ask the AI assistant",
        ],
      },
    ],
  },
};
