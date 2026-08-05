// Ilova ichki interfeysi uchun tarjimalar (sidebar + barcha sahifalar), uz/ru/en.

import type { Lang } from "./landing-content";

export interface AppStrings {
  search: string;
  logout: string;
  privacy: string;
  myProfile: string;
  language: string;
  toggleTheme: string;
  collapseMenu: string;
  notifications: string;
  noNotifications: string;
  roleLabels: Record<string, string>;
  nav: {
    sectionGeneral: string;
    sectionKindergarten: string;
    sectionFinance: string;
    sectionOther: string;
    myGroup: string;
    dashboard: string;
    reports: string;
    children: string;
    groups: string;
    attendance: string;
    staff: string;
    payments: string;
    expenses: string;
    parents: string;
    settings: string;
  };
  common: {
    name: string;
    fullName: string;
    firstName: string;
    lastName: string;
    birthDate: string;
    guardians: string;
    status: string;
    active: string;
    inactive: string;
    capacity: string;
    branch: string;
    role: string;
    phone: string;
    email: string;
    empty: string;
    save: string;
    add: string;
    edit: string;
    create: string;
    cancel: string;
    close: string;
    saving: string;
    date: string;
    period: string;
    from: string;
    to: string;
    apply: string;
    search: string;
    all: string;
    loading: string;
    nothingFound: string;
    nothingFoundSub: string;
    clearFilters: string;
    errTitle: string;
    errSub: string;
    retry: string;
    showing: string;
    of: string;
    sum: string;
    mln: string;
    optional: string;
    required: string;
    invalidPhone: string;
    invalidNumber: string;
    yes: string;
    no: string;
    confirm: string;
    deactivate: string;
    deactivateTitle: string;
    reverse: string;
    reverseTitle: string;
    reverseDone: string;
    saved: string;
    view: string;
    back: string;
    next: string;
    finish: string;
    reason: string;
    newLabel: string;
    whatAdd: string;
    quickPick: string;
    thisMonth: string;
    prevMonth: string;
    quarter: string;
    year: string;
    markRead: string;
    print: string;
  };
  /** Topbardagi "+ Yangi" oynasi: har bir amal ostidagi izoh. */
  quick: {
    childSub: string;
    paymentSub: string;
    expenseSub: string;
    staffSub: string;
    groupSub: string;
    messageSub: string;
  };
  dashboard: {
    title: string;
    subtitle: string;
    period: string;
    netProfit: string;
    margin: string;
    income: string;
    outcome: string;
    breakeven: string;
    aboveBreakeven: string;
    lastMonth: string;
    biggest: string;
    payroll: string;
    todayAttendance: string;
    present: string;
    sick: string;
    absent: string;
    debt: string;
    families: string;
    over30: string;
    chartTitle: string;
    chartSub: string;
    expenseStructure: string;
    agingTitle: string;
    agingSub: string;
    notDue: string;
    aging1_30: string;
    aging31_60: string;
    aging60plus: string;
    sendReminders: string;
    unitTitle: string;
    unitSub: string;
    uFee: string;
    uVariable: string;
    uFixed: string;
    uMargin: string;
    uOther: string;
    unitNote: string;
    quickActions: string;
    recentPayments: string;
    viewAll: string;
    method: string;
    noBreakEven: string;
    trendTitle: string;
    collectedLabel: string;
  };
  children: {
    title: string;
    subtitle: string;
    addChild: string;
    editChild: string;
    aboutChild: string;
    gender: string;
    boy: string;
    girl: string;
    medicalNotes: string;
    medicalHint: string;
    group: string;
    parent: string;
    guardianSection: string;
    relation: string;
    rMother: string;
    rFather: string;
    rRelative: string;
    rOther: string;
    canPickUp: string;
    receivesNotifications: string;
    financialTerms: string;
    discount: string;
    discountNone: string;
    discountSibling: string;
    discountStaffChild: string;
    discountSocial: string;
    discountOther: string;
    discountPercent: string;
    startDate: string;
    status: string;
    active: string;
    waiting: string;
    left: string;
    filterActive: string;
    filterWaiting: string;
    filterLeft: string;
    filterDebt: string;
    transferGroup: string;
    currentGroup: string;
    newGroup: string;
    effectiveDate: string;
    transfer: string;
    transferHint: string;
    transferDone: string;
    deactivateBody: string;
    savedChild: string;
    addGuardian: string;
    guardianAdded: string;
    importTitle: string;
    importAction: string;
    importUploadStep: string;
    importChooseFile: string;
    importPreviewStep: string;
    importConfirmStep: string;
    importRowNumber: string;
    importErrors: string;
    importValidRows: string;
    importTotalRows: string;
    importGroup: string;
    importConfirmButton: string;
    importDone: string;
    importDryRunHint: string;
  };
  groups: {
    title: string;
    subtitle: string;
    addGroup: string;
    editGroup: string;
    groupName: string;
    ageRange: string;
    capacityField: string;
    monthlyFee: string;
    monthlyRevenue: string;
    ageYears: string;
    roomNumber: string;
    mainTeacher: string;
    assignTeacher: string;
    occupancy: string;
    placesFree: string;
    full: string;
    noTeacher: string;
    deactivateBody: string;
    savedGroup: string;
    teacherAssigned: string;
  };
  attendance: {
    title: string;
    subtitle: string;
    chooseGroup: string;
    markAll: string;
    saveAndSend: string;
    saved: string;
    present: string;
    absent: string;
    late: string;
    excused: string;
    sick: string;
    trend: string;
    trendSub: string;
    rate: string;
  };
  payments: {
    title: string;
    subtitle: string;
    billed: string;
    collected: string;
    outstanding: string;
    progress: string;
    takePayment: string;
    newPayment: string;
    paymentMethod: string;
    cash: string;
    card: string;
    terminal: string;
    bank: string;
    other: string;
    amount: string;
    prevDebt: string;
    toPay: string;
    savePayment: string;
    paymentDone: string;
    generateInvoices: string;
    dueDate: string;
    invoicesCreated: string;
    invoicesSkipped: string;
    cancelInvoice: string;
    cancelDone: string;
    paid: string;
    partial: string;
    unpaid: string;
    filterPaid: string;
    filterPartial: string;
    filterUnpaid: string;
    child: string;
  };
  expenses: {
    title: string;
    subtitle: string;
    addExpense: string;
    category: string;
    vendor: string;
    description: string;
    recurring: string;
    manageCategories: string;
    newCategory: string;
    categoryName: string;
    variableFlag: string;
    variableHint: string;
    total: string;
    byCategory: string;
  };
  staff: {
    title: string;
    subtitle: string;
    addStaff: string;
    editStaff: string;
    position: string;
    salary: string;
    hireDate: string;
    employmentType: string;
    fullTime: string;
    partTime: string;
    hourly: string;
    passportNumber: string;
    payrollFund: string;
    personalInfo: string;
    workInfo: string;
    accessInfo: string;
    login: string;
    password: string;
    savedStaff: string;
    deactivateBody: string;
    filterAll: string;
    payrollRunTitle: string;
    payrollRunAction: string;
    baseSalary: string;
    bonus: string;
    deduction: string;
    advanceDeducted: string;
    netPay: string;
    payrollHistory: string;
    payrollPeriod: string;
    payrollStatus: string;
    payrollRecorded: string;
    payrollReversed: string;
    payrollPaidAt: string;
    payrollSaved: string;
    payrollReverseConfirm: string;
  };
  reports: {
    title: string;
    subtitle: string;
    plTitle: string;
    revenueSection: string;
    expenseSection: string;
    totalRevenue: string;
    totalExpenses: string;
    netTotal: string;
    readyReports: string;
    repPl: string;
    repRevenueByGroup: string;
    repExpenses: string;
    downloadCsv: string;
    revenue: string;
    expensesTotal: string;
    net: string;
    revenueByGroup: string;
  };
  pages: {
    children: string;
    groups: string;
    billing: string;
    staff: string;
    chooseChild: string;
    chooseBranch: string;
    chooseGroup: string;
  };
  messaging: {
    title: string;
    subtitle: string;
    connectedFamilies: string;
    sentThisMonth: string;
    autoNotifications: string;
    notifChildCheckedIn: string;
    notifChildSick: string;
    notifPaymentReminder: string;
    notifDebtWarning: string;
    notifBirthdayGreeting: string;
    broadcastTitle: string;
    audience: string;
    audienceAll: string;
    audienceGroup: string;
    audienceDebtors: string;
    messageText: string;
    send: string;
    sent: string;
    queuedCount: string;
    parentsListTitle: string;
    messagesUnit: string;
    autoNotificationsSub: string;
    broadcastSub: string;
    messagePlaceholder: string;
    sendHint: string;
    hintCheckedIn: string;
    hintSick: string;
    hintPaymentReminder: string;
    hintDebtWarning: string;
    hintBirthday: string;
    inviteGet: string;
    inviteTitle: string;
    inviteSubtitle: string;
    inviteSteps: string;
    inviteExpires: string;
    inviteCopy: string;
    inviteCopied: string;
    inviteAlreadyLinked: string;
  };
  food: {
    productsTitle: string;
    productsSub: string;
    addProduct: string;
    unit: string;
    unitCost: string;
    stock: string;
    stockMovement: string;
    movementIn: string;
    movementOut: string;
    quantity: string;
    reason: string;
    reasonPurchase: string;
    reasonConsumption: string;
    reasonAdjustment: string;
    reasonWaste: string;
    mealsTitle: string;
    mealsSub: string;
    addMeal: string;
    ingredients: string;
    addIngredient: string;
    perServing: string;
    serve: string;
    serveTitle: string;
    servings: string;
    noStock: string;
    reportTitle: string;
    reportSub: string;
    opening: string;
    stockIn: string;
    stockOut: string;
    closing: string;
    value: string;
    totalValue: string;
  };
  settings: {
    title: string;
    subtitle: string;
    profileSection: string;
    name: string;
    legalName: string;
    address: string;
    hoursText: string;
    autoInvoiceDay: string;
    autoInvoiceDayHint: string;
    saved: string;
    saveChanges: string;
    tariffs: string;
    tariffsSub: string;
    months: string;
  };
}

type Table = Record<string, [string, string, string]>;

// Har bir satr: [uz, ru, en]. `build()` shu jadvaldan Record<Lang, AppStrings> yasaydi.
const T: Table = {
  search: ["Qidirish", "Поиск", "Search"],
  logout: ["Chiqish", "Выйти", "Sign out"],
  privacy: ["Maxfiylik siyosati", "Политика конфиденциальности", "Privacy policy"],
  myProfile: ["Mening profilim", "Мой профиль", "My profile"],
  language: ["Til", "Язык", "Language"],
  toggleTheme: ["Mavzuni almashtirish", "Сменить тему", "Toggle theme"],
  collapseMenu: [
    "Menyuni yig'ish / yozish",
    "Свернуть / развернуть меню",
    "Collapse / expand menu",
  ],
  notifications: ["Bildirishnomalar", "Уведомления", "Notifications"],
  noNotifications: [
    "Yangi bildirishnoma yo'q",
    "Нет новых уведомлений",
    "No new notifications",
  ],

  roleOwner: ["Rahbar", "Руководитель", "Owner"],
  roleManager: ["Menejer", "Менеджер", "Manager"],
  roleTeacher: ["Tarbiyachi", "Воспитатель", "Teacher"],
  roleParent: ["Ota-ona", "Родитель", "Parent"],

  navSectionGeneral: ["Umumiy", "Общее", "General"],
  navSectionKindergarten: ["Bog'cha", "Детский сад", "Kindergarten"],
  navSectionFinance: ["Moliya", "Финансы", "Finance"],
  navSectionOther: ["Boshqa", "Прочее", "Other"],
  navMyGroup: ["Mening guruhim", "Моя группа", "My group"],
  navDashboard: ["Boshqaruv paneli", "Панель управления", "Dashboard"],
  navReports: ["Hisobotlar", "Отчёты", "Reports"],
  navChildren: ["Bolalar", "Дети", "Children"],
  navGroups: ["Guruhlar", "Группы", "Groups"],
  navAttendance: ["Davomat", "Посещаемость", "Attendance"],
  navStaff: ["Xodimlar", "Сотрудники", "Staff"],
  navPayments: ["To'lovlar", "Оплаты", "Payments"],
  navExpenses: ["Xarajatlar", "Расходы", "Expenses"],
  navParents: ["Ota-onalar", "Родители", "Parents"],
  navSettings: ["Sozlamalar", "Настройки", "Settings"],

  name: ["Ism", "Имя", "Name"],
  fullName: ["F.I.O.", "Ф.И.О.", "Full name"],
  firstName: ["Ismi", "Имя", "First name"],
  lastName: ["Familiyasi", "Фамилия", "Last name"],
  birthDate: ["Tug'ilgan sana", "Дата рождения", "Birth date"],
  guardians: ["Vasiylar", "Опекуны", "Guardians"],
  status: ["Holat", "Статус", "Status"],
  active: ["Faol", "Активен", "Active"],
  inactive: ["Nofaol", "Неактивен", "Inactive"],
  capacity: ["Sig'im", "Вместимость", "Capacity"],
  branch: ["Filial", "Филиал", "Branch"],
  role: ["Rol", "Роль", "Role"],
  phone: ["Telefon", "Телефон", "Phone"],
  email: ["Email", "Email", "Email"],
  empty: ["Ma'lumot yo'q.", "Нет данных.", "No data."],
  save: ["Saqlash", "Сохранить", "Save"],
  add: ["Qo'shish", "Добавить", "Add"],
  edit: ["Tahrirlash", "Редактировать", "Edit"],
  create: ["Yaratish", "Создать", "Create"],
  cancel: ["Bekor qilish", "Отмена", "Cancel"],
  close: ["Yopish", "Закрыть", "Close"],
  saving: ["Saqlanmoqda...", "Сохранение...", "Saving..."],
  date: ["Sana", "Дата", "Date"],
  period: ["Davr", "Период", "Period"],
  from: ["Boshlanish", "Начало", "From"],
  to: ["Tugash", "Конец", "To"],
  apply: ["Qo'llash", "Применить", "Apply"],
  commonSearch: ["Qidiruv...", "Поиск...", "Search..."],
  all: ["Barchasi", "Все", "All"],
  loading: ["Yuklanmoqda...", "Загрузка...", "Loading..."],
  nothingFound: ["Hech narsa topilmadi", "Ничего не найдено", "Nothing found"],
  nothingFoundSub: [
    "Qidiruv so'zini o'zgartiring yoki filtrlarni tozalang",
    "Измените запрос или сбросьте фильтры",
    "Try a different search or clear the filters",
  ],
  clearFilters: ["Filtrlarni tozalash", "Сбросить фильтры", "Clear filters"],
  errTitle: ["Ma'lumot yuklanmadi", "Не удалось загрузить", "Couldn't load data"],
  errSub: [
    "Internet aloqasini tekshiring va qayta urinib ko'ring",
    "Проверьте соединение и попробуйте снова",
    "Check your connection and try again",
  ],
  retry: ["Qayta urinish", "Повторить", "Retry"],
  showing: ["Ko'rsatilmoqda", "Показано", "Showing"],
  of: ["dan", "из", "of"],
  sum: ["so'm", "сум", "UZS"],
  mln: ["mln", "млн", "M"],
  optional: ["ixtiyoriy", "необязательно", "optional"],
  required: [
    "Bu maydon to'ldirilishi shart",
    "Это поле обязательно",
    "This field is required",
  ],
  invalidPhone: [
    "Telefon raqam noto'g'ri (+998 XX XXX XX XX)",
    "Неверный номер (+998 XX XXX XX XX)",
    "Invalid phone (+998 XX XXX XX XX)",
  ],
  invalidNumber: ["Faqat raqam kiriting", "Введите только цифры", "Numbers only"],
  yes: ["Ha", "Да", "Yes"],
  no: ["Yo'q", "Нет", "No"],
  confirm: ["Tasdiqlash", "Подтвердить", "Confirm"],
  deactivate: ["Faolsizlantirish", "Деактивировать", "Deactivate"],
  deactivateTitle: ["Faolsizlantirishni tasdiqlang", "Подтвердите деактивацию", "Confirm deactivation"],
  reverse: ["Bekor qilish", "Отменить", "Reverse"],
  reverseTitle: ["Bekor qilishni tasdiqlang", "Подтвердите отмену", "Confirm reversal"],
  reverseDone: ["Bekor qilindi", "Отменено", "Reversed"],
  saved: ["Saqlandi", "Сохранено", "Saved"],
  view: ["Ko'rish", "Просмотр", "View"],
  back: ["Orqaga", "Назад", "Back"],
  next: ["Keyingisi", "Далее", "Next"],
  finish: ["Yakunlash", "Завершить", "Finish"],
  reason: ["Sabab", "Причина", "Reason"],

  dashTitle: ["Boshqaruv paneli", "Панель управления", "Dashboard"],
  dashSubtitle: [
    "Bog'changizning umumiy holati",
    "Общее состояние вашего сада",
    "Your kindergarten at a glance",
  ],
  dashPeriod: ["Davr", "Период", "Period"],
  dashNetProfit: ["Sof foyda", "Чистая прибыль", "Net profit"],
  dashMargin: ["foyda ulushi", "доля прибыли", "margin"],
  dashIncome: ["Daromad", "Доход", "Revenue"],
  dashOutcome: ["Xarajat", "Расход", "Expenses"],
  dashBreakeven: ["Zararsizlik", "Безубыточность", "Break-even"],
  dashAboveBreakeven: [
    "Zararsizlik chizig'idan yuqori",
    "Выше точки безубыточности",
    "Above break-even",
  ],
  dashLastMonth: ["O'tgan davr", "Прошлый период", "Last period"],
  dashBiggest: ["Eng katta", "Крупнейший", "Largest"],
  dashPayroll: ["ish haqi", "зарплата", "payroll"],
  dashTodayAtt: ["Bugungi davomat", "Посещаемость сегодня", "Today's attendance"],
  dashPresent: ["keldi", "пришли", "present"],
  dashSick: ["kasal", "болеют", "sick"],
  dashAbsent: ["kelmadi", "не пришли", "absent"],
  dashDebt: ["Qarz", "Долг", "Debt"],
  dashFamilies: ["oila", "семей", "families"],
  dashOver30: ["30 kundan ortiq", "более 30 дней", "over 30 days"],
  dashChartTitle: ["Daromad va xarajat", "Доход и расход", "Revenue and expenses"],
  dashChartSub: [
    "So'nggi 6 oy, mln so'mda",
    "Последние 6 месяцев, млн сум",
    "Last 6 months, millions UZS",
  ],
  dashExpStructure: ["Xarajat tuzilishi", "Структура расходов", "Expense breakdown"],
  dashAgingTitle: ["To'lov kechikishi", "Просрочка оплаты", "Payment delays"],
  dashAgingSub: [
    "Kim bilan bugun gaplashish kerak",
    "С кем связаться сегодня",
    "Who to follow up with today",
  ],
  dashNotDue: ["Muddati kelmagan", "Срок не наступил", "Not yet due"],
  dashAging1_30: ["1-30 kun kechikkan", "Просрочка 1-30 дней", "1-30 days late"],
  dashAging31_60: ["31-60 kun kechikkan", "Просрочка 31-60 дней", "31-60 days late"],
  dashAging60plus: ["60 kundan ortiq", "Более 60 дней", "Over 60 days"],
  dashSendReminders: [
    "Qarzdorlarga eslatma yuborish",
    "Отправить напоминание должникам",
    "Send payment reminders",
  ],
  dashUnitTitle: ["Bitta bola bo'yicha hisob", "Расчёт на одного ребёнка", "Per-child breakdown"],
  dashUnitSub: [
    "Faol bolalar soniga bo'lingan",
    "В расчёте на активного ребёнка",
    "Per active child, current period",
  ],
  dashUFee: ["To'lov (bola boshiga)", "Оплата (на ребёнка)", "Fee (per child)"],
  dashUVariable: ["O'zgaruvchan xarajat", "Переменные расходы", "Variable cost"],
  dashUFixed: ["Doimiy xarajat", "Постоянные расходы", "Fixed costs"],
  dashUMargin: ["Marjinal daromad", "Маржинальный доход", "Contribution margin"],
  dashUOther: ["Boshqa xarajat", "Прочие расходы", "Other costs"],
  dashUnitNote: [
    "Zararsizlikka chiqish uchun kerakli bolalar soni",
    "Детей нужно для выхода на безубыточность",
    "Children needed to break even",
  ],
  dashQuickActions: ["Tezkor amallar", "Быстрые действия", "Quick actions"],
  dashRecentPayments: ["So'nggi to'lovlar", "Последние оплаты", "Recent payments"],
  dashViewAll: ["Barchasi", "Все", "View all"],
  dashMethod: ["Usul", "Способ", "Method"],
  dashNoBreakEven: [
    "Hisoblash uchun ma'lumot yetarli emas",
    "Недостаточно данных для расчёта",
    "Not enough data to calculate"],
  dashTrendTitle: [
    "So'nggi kunlar davomati",
    "Посещаемость за последние дни",
    "Attendance over recent days",
  ],
  dashCollectedLabel: ["Yig'ilgan", "Собрано", "Collected"],

  childrenTitle: ["Bolalar", "Дети", "Children"],
  childrenSubtitle: [
    "Bolalar ro'yxati va enrollment",
    "Список детей и зачисления",
    "Children list and enrollment",
  ],
  addChild: ["Bola qo'shish", "Добавить ребёнка", "Add child"],
  editChild: ["Bolani tahrirlash", "Редактировать ребёнка", "Edit child"],
  aboutChild: ["Bola haqida", "О ребёнке", "About the child"],
  gender: ["Jinsi", "Пол", "Gender"],
  boy: ["O'g'il bola", "Мальчик", "Boy"],
  girl: ["Qiz bola", "Девочка", "Girl"],
  medicalNotes: ["Tibbiy eslatma", "Медицинская заметка", "Medical note"],
  medicalHint: [
    "Allergiya, surunkali kasallik, doimiy dori",
    "Аллергия, хронические заболевания, лекарства",
    "Allergies, chronic conditions, medication",
  ],
  group: ["Guruh", "Группа", "Group"],
  parent: ["Ota-ona", "Родитель", "Parent"],
  guardianSection: ["Ota-ona / vasiy", "Родитель / опекун", "Parent / guardian"],
  relation: ["Qarindoshlik", "Родство", "Relation"],
  rMother: ["Onasi", "Мать", "Mother"],
  rFather: ["Otasi", "Отец", "Father"],
  rRelative: ["Qarindosh", "Родственник", "Relative"],
  rOther: ["Boshqa", "Другое", "Other"],
  canPickUp: [
    "Bolani olib ketishga ruxsat",
    "Может забирать ребёнка",
    "Can pick up the child",
  ],
  receivesNotifications: [
    "Bildirishnoma oladi",
    "Получает уведомления",
    "Receives notifications",
  ],
  financialTerms: ["Moliyaviy shartlar", "Финансовые условия", "Financial terms"],
  discount: ["Chegirma", "Скидка", "Discount"],
  discountNone: ["Yo'q", "Нет", "None"],
  discountSibling: ["Aka-uka/opa-singil 10%", "Скидка за брата/сестру 10%", "Sibling 10%"],
  discountStaffChild: ["Xodim bolasi 50%", "Ребёнок сотрудника 50%", "Staff child 50%"],
  discountSocial: ["Ijtimoiy himoya 100%", "Соцзащита 100%", "Social support 100%"],
  discountOther: ["Boshqa", "Другое", "Other"],
  discountPercent: ["Chegirma foizi (%)", "Процент скидки (%)", "Discount percent (%)"],
  startDate: [
    "Kelishi kerak bo'lgan sana",
    "Дата начала посещения",
    "Start date",
  ],
  childStatus: ["Holat", "Статус", "Status"],
  statusActive: ["Faol", "Активен", "Active"],
  statusWaiting: ["Navbatda", "В очереди", "Waiting"],
  statusLeft: ["Chiqib ketgan", "Выбыл", "Left"],
  filterActive: ["Faol", "Активные", "Active"],
  filterWaiting: ["Navbatda", "В очереди", "Waiting"],
  filterLeft: ["Chiqib ketgan", "Выбывшие", "Left"],
  filterDebt: ["Qarzdor", "С долгом", "In debt"],
  transferGroup: ["Guruhni o'zgartirish", "Перевести в другую группу", "Change group"],
  currentGroup: ["Hozirgi guruh", "Текущая группа", "Current group"],
  newGroup: ["Yangi guruh", "Новая группа", "New group"],
  effectiveDate: ["O'tkazish sanasi", "Дата перевода", "Effective date"],
  transfer: ["O'tkazish", "Перевести", "Transfer"],
  transferHint: [
    "Eski guruhdagi a'zolik shu sanada yopiladi, yangisi ochiladi.",
    "Членство в старой группе закроется на эту дату, откроется новое.",
    "The old group membership closes on this date, a new one opens.",
  ],
  transferDone: ["Bola guruhi o'zgartirildi", "Группа ребёнка изменена", "Child transferred"],
  deactivateChildBody: [
    "Bola faolsizlantiriladi. Tarixi (davomat, to'lovlar) saqlanib qoladi.",
    "Ребёнок будет деактивирован. История (посещаемость, оплаты) сохранится.",
    "The child will be deactivated. History (attendance, payments) is kept.",
  ],
  savedChild: ["Bola ma'lumoti saqlandi", "Данные ребёнка сохранены", "Child saved"],
  addGuardian: ["Vasiy qo'shish", "Добавить опекуна", "Add guardian"],
  guardianAdded: ["Vasiy qo'shildi", "Опекун добавлен", "Guardian added"],
  importTitle: ["Excel'dan import", "Импорт из Excel", "Import from Excel"],
  importAction: ["Import qilish", "Импортировать", "Import"],
  importUploadStep: ["Faylni tanlang", "Выберите файл", "Choose a file"],
  importChooseFile: ["Fayl tanlash (.xlsx yoki .csv)", "Выбрать файл (.xlsx или .csv)", "Choose file (.xlsx or .csv)"],
  importPreviewStep: ["Ko'rib chiqish", "Просмотр", "Preview"],
  importConfirmStep: ["Tasdiqlash", "Подтверждение", "Confirm"],
  importRowNumber: ["Qator", "Строка", "Row"],
  importErrors: ["Xatolar", "Ошибки", "Errors"],
  importValidRows: ["To'g'ri qatorlar", "Корректных строк", "Valid rows"],
  importTotalRows: ["Jami qatorlar", "Всего строк", "Total rows"],
  importGroup: ["Qaysi guruhga qo'shilsin", "В какую группу добавить", "Which group to add to"],
  importConfirmButton: ["Tasdiqlash va import qilish", "Подтвердить и импортировать", "Confirm and import"],
  importDone: ["ta bola import qilindi", "детей импортировано", "children imported"],
  importDryRunHint: [
    "Bu faqat ko'rib chiqish — hech narsa saqlanmaydi",
    "Это только просмотр — ничего не сохраняется",
    "This is preview only — nothing is saved yet",
  ],

  groupsTitle: ["Guruhlar", "Группы", "Groups"],
  groupsSubtitle: [
    "Guruhlar, tarif va tarbiyachilar",
    "Группы, тарифы и воспитатели",
    "Groups, tariffs and teachers",
  ],
  addGroup: ["Guruh qo'shish", "Добавить группу", "Add group"],
  editGroup: ["Guruhni tahrirlash", "Редактировать группу", "Edit group"],
  groupName: ["Guruh nomi", "Название группы", "Group name"],
  ageRange: ["Yosh oralig'i (oy)", "Возрастной диапазон (мес.)", "Age range (months)"],
  capacityField: ["Sig'im (bola soni)", "Вместимость (детей)", "Capacity (children)"],
  monthlyFee: ["Oylik tarif", "Ежемесячный тариф", "Monthly fee"],
  roomNumber: ["Xona raqami", "Номер комнаты", "Room number"],
  mainTeacher: ["Asosiy tarbiyachi", "Основной воспитатель", "Lead teacher"],
  assignTeacher: ["Tarbiyachi biriktirish", "Назначить воспитателя", "Assign teacher"],
  occupancy: ["To'ldirilganlik", "Заполненность", "Occupancy"],
  placesFree: ["joy bo'sh", "мест свободно", "places free"],
  full: ["Joy yo'q", "Мест нет", "Full"],
  noTeacher: ["Tarbiyachisiz", "Без воспитателя", "No teacher"],
  deactivateGroupBody: [
    "Guruh faolsizlantiriladi. Bolalarni avval boshqa guruhga o'tkazing.",
    "Группа будет деактивирована. Сначала переведите детей в другую группу.",
    "The group will be deactivated. Move the children to another group first.",
  ],
  savedGroup: ["Guruh saqlandi", "Группа сохранена", "Group saved"],
  teacherAssigned: ["Tarbiyachi biriktirildi", "Воспитатель назначен", "Teacher assigned"],

  attTitle: ["Davomat", "Посещаемость", "Attendance"],
  attSubtitle: [
    "Guruh bo'yicha kunlik davomat",
    "Ежедневная посещаемость по группам",
    "Daily attendance by group",
  ],
  attChooseGroup: ["Guruhni tanlang", "Выберите группу", "Choose a group"],
  attMarkAll: [
    "Hammasini \"keldi\" qilish",
    "Отметить всех присутствующими",
    "Mark all present",
  ],
  attSaveAndSend: ["Saqlash", "Сохранить", "Save"],
  attSaved: ["Davomat saqlandi", "Посещаемость сохранена", "Attendance saved"],
  attPresent: ["Keldi", "Пришёл", "Present"],
  attAbsent: ["Kelmadi", "Не пришёл", "Absent"],
  attLate: ["Kechikdi", "Опоздал", "Late"],
  attExcused: ["Sababli", "Уважительная причина", "Excused"],
  attSick: ["Kasal", "Болеет", "Sick"],
  attTrend: ["Davomat trendi", "Тренд посещаемости", "Attendance trend"],
  attTrendSub: [
    "So'nggi 11 kun",
    "Последние 11 дней",
    "Last 11 days",
  ],
  attRate: ["Davomat", "Посещаемость", "Attendance rate"],

  payTitle: ["To'lovlar", "Оплаты", "Payments"],
  paySubtitle: [
    "Hisob-fakturalar va to'lovlar",
    "Счета и оплаты",
    "Invoices and payments",
  ],
  payBilled: ["Hisoblangan", "Начислено", "Billed"],
  payCollected: ["Yig'ilgan", "Собрано", "Collected"],
  payOutstanding: ["Qoldiq", "Остаток", "Outstanding"],
  payProgress: ["Bajarilishi", "Выполнение", "Progress"],
  payTakePayment: ["To'lov qabul qilish", "Принять оплату", "Record payment"],
  payNewPayment: ["Yangi to'lov", "Новая оплата", "New payment"],
  payMethod: ["To'lov usuli", "Способ оплаты", "Payment method"],
  payCash: ["Naqd", "Наличные", "Cash"],
  payCard: ["Karta", "Карта", "Card"],
  payTerminal: ["Terminal", "Терминал", "Terminal"],
  payBank: ["Bank", "Банк", "Bank"],
  payOther: ["Boshqa", "Другое", "Other"],
  payAmount: ["Summa", "Сумма", "Amount"],
  payPrevDebt: ["Oldingi qarz", "Предыдущий долг", "Previous debt"],
  payToPay: ["To'lanadigan", "К оплате", "Amount due"],
  paySavePayment: ["To'lovni saqlash", "Сохранить оплату", "Save payment"],
  payDone: ["To'lov qabul qilindi", "Оплата принята", "Payment recorded"],
  payGenerateInvoices: [
    "Hisob-faktura yaratish",
    "Создать счета",
    "Generate invoices",
  ],
  payDueDate: ["To'lov muddati", "Срок оплаты", "Due date"],
  payInvoicesCreated: ["ta hisob-faktura yaratildi", "счетов создано", "invoices created"],
  payInvoicesSkipped: ["ta o'tkazib yuborildi", "пропущено", "skipped"],
  payCancelInvoice: ["Hisob-fakturani bekor qilish", "Отменить счёт", "Cancel invoice"],
  payCancelDone: ["Bekor qilindi", "Отменено", "Cancelled"],
  payPaid: ["To'langan", "Оплачено", "Paid"],
  payPartial: ["Qisman", "Частично", "Partial"],
  payUnpaid: ["To'lanmagan", "Не оплачено", "Unpaid"],
  payFilterPaid: ["To'langan", "Оплаченные", "Paid"],
  payFilterPartial: ["Qisman", "Частично", "Partial"],
  payFilterUnpaid: ["To'lanmagan", "Неоплаченные", "Unpaid"],
  payChild: ["Bola", "Ребёнок", "Child"],

  expTitle: ["Xarajatlar", "Расходы", "Expenses"],
  expSubtitle: [
    "Filial xarajatlari va kategoriyalar",
    "Расходы филиала и категории",
    "Branch expenses and categories",
  ],
  addExpense: ["Xarajat qo'shish", "Добавить расход", "Add expense"],
  category: ["Kategoriya", "Категория", "Category"],
  vendor: ["Yetkazib beruvchi", "Поставщик", "Vendor"],
  description: ["Izoh", "Комментарий", "Description"],
  recurring: [
    "Har oy takrorlanadigan xarajat",
    "Ежемесячный повторяющийся расход",
    "Recurring monthly expense",
  ],
  manageCategories: ["Kategoriyalar", "Категории", "Categories"],
  newCategory: ["Yangi kategoriya", "Новая категория", "New category"],
  categoryName: ["Kategoriya nomi", "Название категории", "Category name"],
  variableFlag: [
    "O'zgaruvchan xarajat (bola soniga bog'liq)",
    "Переменный расход (зависит от числа детей)",
    "Variable cost (scales with children)",
  ],
  variableHint: [
    "Zararsizlik hisobida o'zgaruvchan xarajat sifatida hisoblanadi",
    "Учитывается как переменный расход в расчёте безубыточности",
    "Counted as a variable cost in the break-even calculation",
  ],
  expTotal: ["Jami", "Итого", "Total"],
  expByCategory: ["Kategoriya kesimida", "В разрезе категорий", "By category"],

  staffTitle: ["Xodimlar", "Сотрудники", "Staff"],
  staffSubtitle: [
    "Xodimlar ro'yxati va ish haqi fondi",
    "Список сотрудников и фонд зарплаты",
    "Staff list and payroll fund",
  ],
  addStaff: ["Xodim qo'shish", "Добавить сотрудника", "Add employee"],
  editStaff: ["Xodimni tahrirlash", "Редактировать сотрудника", "Edit employee"],
  position: ["Lavozim", "Должность", "Position"],
  salary: ["Oylik maosh", "Оклад", "Monthly salary"],
  hireDate: ["Ishga kirgan sana", "Дата приёма", "Hire date"],
  employmentType: ["Ish turi", "Тип занятости", "Employment type"],
  fullTime: ["To'liq stavka", "Полная ставка", "Full-time"],
  partTime: ["Yarim stavka", "Половина ставки", "Part-time"],
  hourly: ["Soatbay", "Почасовая", "Hourly"],
  passportNumber: ["Passport seriya raqami", "Серия и номер паспорта", "Passport number"],
  payrollFund: ["Ish haqi fondi", "Фонд зарплаты", "Payroll fund"],
  personalInfo: ["Shaxsiy ma'lumotlar", "Личные данные", "Personal info"],
  workInfo: ["Ish ma'lumotlari", "Рабочая информация", "Employment"],
  accessInfo: ["Tizimga kirish", "Доступ в систему", "System access"],
  staffLogin: ["Login", "Логин", "Username"],
  staffPassword: ["Parol", "Пароль", "Password"],
  savedStaff: ["Xodim ma'lumoti saqlandi", "Данные сотрудника сохранены", "Staff saved"],
  deactivateStaffBody: [
    "Xodim faolsizlantiriladi va tizimga kira olmaydi.",
    "Сотрудник будет деактивирован и не сможет войти в систему.",
    "The employee will be deactivated and unable to sign in.",
  ],
  staffFilterAll: ["Barchasi", "Все", "All"],
  payrollRunTitle: ["Oylikni hisoblash va to'lash", "Расчёт и выплата зарплаты", "Calculate and pay salary"],
  payrollRunAction: ["Hisoblash va to'lash", "Рассчитать и выплатить", "Calculate and pay"],
  baseSalary: ["Asosiy maosh", "Оклад", "Base salary"],
  bonus: ["Bonus", "Премия", "Bonus"],
  deduction: ["Ushlanma", "Удержание", "Deduction"],
  advanceDeducted: ["Avans (ushlangan)", "Аванс (удержан)", "Advance deducted"],
  netPay: ["Sof summa", "К выплате", "Net pay"],
  payrollHistory: ["To'lovlar tarixi", "История выплат", "Payment history"],
  payrollPeriod: ["Davr", "Период", "Period"],
  payrollStatus: ["Holat", "Статус", "Status"],
  payrollRecorded: ["To'langan", "Выплачено", "Paid"],
  payrollReversed: ["Bekor qilingan", "Отменено", "Reversed"],
  payrollPaidAt: ["To'lov sanasi", "Дата выплаты", "Paid at"],
  payrollSaved: ["Oylik hisoblandi va to'landi", "Зарплата рассчитана и выплачена", "Payroll calculated and paid"],
  payrollReverseConfirm: [
    "Bu to'lov bekor qilinadi va bog'liq xarajat ham bekor qilinadi.",
    "Эта выплата и связанный расход будут отменены.",
    "This payment and its linked expense will be reversed.",
  ],

  repTitle: ["Hisobotlar", "Отчёты", "Reports"],
  repSubtitle: [
    "Foyda va zarar, guruh bo'yicha daromad",
    "Прибыль и убытки, доход по группам",
    "Profit & loss, revenue by group",
  ],
  repPlTitle: ["Foyda va zarar", "Прибыль и убытки", "Profit and loss"],
  repRevenue: ["Daromad", "Доход", "Revenue"],
  repExpensesTotal: ["Xarajat", "Расход", "Expenses"],
  repNet: ["Sof natija", "Чистый результат", "Net result"],
  repRevenueByGroup: ["Guruh bo'yicha daromad", "Доход по группам", "Revenue by group"],
  repRevenueSection: ["DAROMAD", "ДОХОД", "REVENUE"],
  repExpenseSection: ["XARAJAT", "РАСХОД", "EXPENSES"],
  repTotalRevenue: ["Jami daromad", "Итого доход", "Total revenue"],
  repTotalExpenses: ["Jami xarajat", "Итого расход", "Total expenses"],
  repNetTotal: ["SOF FOYDA", "ЧИСТАЯ ПРИБЫЛЬ", "NET PROFIT"],
  repReadyReports: ["Tayyor hisobotlar", "Готовые отчёты", "Ready reports"],
  repPlFile: ["Foyda va zarar hisoboti", "Отчёт о прибылях и убытках", "Profit and loss statement"],
  repExpensesFile: ["Kategoriya bo'yicha xarajat", "Расходы по категориям", "Expenses by category"],
  repDownloadCsv: ["CSV yuklab olish", "Скачать CSV", "Download CSV"],

  pageChildren: ["Bolalar", "Дети", "Children"],
  pageGroups: ["Guruhlar", "Группы", "Groups"],
  pageBilling: ["To'lovlar", "Оплаты", "Payments"],
  pageStaff: ["Xodimlar", "Сотрудники", "Staff"],
  chooseChild: ["Bolani tanlang", "Выберите ребёнка", "Choose a child"],
  chooseBranch: ["Filialni tanlang", "Выберите филиал", "Choose a branch"],
  chooseGroup: ["Guruhni tanlang", "Выберите группу", "Choose a group"],

  msgTitle: ["Ota-onalar bilan aloqa", "Связь с родителями", "Parent messaging"],
  msgSubtitle: [
    "Avtomatik bildirishnomalar va ommaviy xabarlar",
    "Автоматические уведомления и массовые рассылки",
    "Automatic notifications and broadcasts",
  ],
  msgConnectedFamilies: ["Ulangan oilalar", "Подключённые семьи", "Connected families"],
  msgSentThisMonth: ["Shu oy yuborilgan", "Отправлено за месяц", "Sent this month"],
  msgAutoNotifications: ["Avtomatik bildirishnomalar", "Автоматические уведомления", "Automatic notifications"],
  msgNotifChildCheckedIn: ["Bola kelganda", "Когда ребёнок пришёл", "When child checks in"],
  msgNotifChildSick: ["Bola kasal deb belgilanganda", "Когда ребёнок отмечен больным", "When child marked sick"],
  msgNotifPaymentReminder: ["To'lov eslatmasi", "Напоминание об оплате", "Payment reminder"],
  msgNotifDebtWarning: ["Qarz haqida ogohlantirish", "Предупреждение о долге", "Debt warning"],
  msgNotifBirthdayGreeting: ["Tug'ilgan kun tabrigi", "Поздравление с днём рождения", "Birthday greeting"],
  msgBroadcastTitle: ["Ommaviy xabar yuborish", "Массовая рассылка", "Send broadcast"],
  msgAudience: ["Auditoriya", "Аудитория", "Audience"],
  msgAudienceAll: ["Barcha ota-onalar", "Все родители", "All parents"],
  msgAudienceGroup: ["Bitta guruh", "Одна группа", "One group"],
  msgAudienceDebtors: ["Qarzdorlar", "Должники", "Debtors"],
  msgMessageText: ["Xabar matni", "Текст сообщения", "Message text"],
  msgSend: ["Yuborish", "Отправить", "Send"],
  msgSent: ["ta ota-onaga yuborildi", "родителям отправлено", "recipients queued"],
  msgQueuedCount: ["Yuborildi", "Отправлено", "Queued"],
  msgParentsListTitle: ["Ota-onalar ro'yxati", "Список родителей", "Parents list"],
  msgMessagesUnit: ["xabar", "сообщений", "messages"],
  msgAutoNotificationsSub: ["Tizim o'zi yuboradi", "Отправляются системой", "Sent automatically"],
  msgBroadcastSub: ["Guruh yoki barchaga", "Группе или всем", "To a group or everyone"],
  msgMessagePlaceholder: [
    "Hurmatli ota-onalar, …",
    "Уважаемые родители, …",
    "Dear parents, …",
  ],
  msgSendHint: [
    "Xabar Telegram orqali yetkaziladi — faqat botga ulangan oilalarga.",
    "Сообщение доставляется через Telegram — только подключённым семьям.",
    "Delivered via Telegram — only to families connected to the bot.",
  ],
  msgInviteGet: ["Kod olish", "Получить код", "Get code"],
  msgInviteTitle: [
    "Telegram taklif kodi",
    "Пригласительный код Telegram",
    "Telegram invitation code",
  ],
  msgInviteSubtitle: [
    "Kodni ota-onaga bering — u bir marta ishlatiladi.",
    "Передайте код родителю — он одноразовый.",
    "Give the code to the parent — it works once.",
  ],
  msgInviteSteps: [
    "Ota-ona botni ochadi va shu kodni yuboradi. Shundan so'ng u farzandining davomati, kunlik hisoboti va to'lovlarini Telegram orqali ko'ra oladi.",
    "Родитель открывает бот и отправляет этот код. После этого он сможет видеть посещаемость, отчёты и оплаты ребёнка в Telegram.",
    "The parent opens the bot and sends this code. After that they can see their child's attendance, reports and payments in Telegram.",
  ],
  msgInviteExpires: ["Amal qilish muddati", "Действителен до", "Valid until"],
  msgInviteCopy: ["Nusxalash", "Копировать", "Copy"],
  msgInviteCopied: ["Nusxalandi", "Скопировано", "Copied"],
  msgInviteAlreadyLinked: [
    "Bu ota-ona allaqachon botga ulangan.",
    "Этот родитель уже подключён к боту.",
    "This parent is already connected to the bot.",
  ],
  msgHintCheckedIn: [
    "Davomatda \"keldi\" belgilanganda darhol",
    "Сразу при отметке присутствия",
    "Immediately when marked present",
  ],
  msgHintSick: [
    "Davomatda \"kasal\" belgilanganda",
    "При отметке \"болеет\"",
    "When marked sick in attendance",
  ],
  msgHintPaymentReminder: [
    "Har oyning 1 va 10-sanasida",
    "1-го и 10-го числа",
    "On the 1st and 10th",
  ],
  msgHintDebtWarning: [
    "To'lov 15 kun kechikkanda",
    "При просрочке 15 дней",
    "After 15 days overdue",
  ],
  msgHintBirthday: [
    "Bolaning tug'ilgan kunida",
    "В день рождения ребёнка",
    "On the child's birthday",
  ],

  foodProductsTitle: ["Mahsulotlar", "Продукты", "Products"],
  foodProductsSub: [
    "Ombor qoldig'i va tannarx",
    "Складские остатки и себестоимость",
    "Stock balance and unit cost",
  ],
  foodAddProduct: ["Mahsulot qo'shish", "Добавить продукт", "Add product"],
  foodUnit: ["O'lchov birligi", "Единица измерения", "Unit"],
  foodUnitCost: ["Tannarx (birlik)", "Себестоимость (ед.)", "Unit cost"],
  foodStock: ["Qoldiq", "Остаток", "Stock"],
  foodStockMovement: ["Kirim / chiqim", "Приход / расход", "Stock movement"],
  foodMovementIn: ["Kirim", "Приход", "In"],
  foodMovementOut: ["Chiqim", "Расход", "Out"],
  foodQuantity: ["Miqdor", "Количество", "Quantity"],
  foodReason: ["Sabab", "Причина", "Reason"],
  foodReasonPurchase: ["Xarid", "Закупка", "Purchase"],
  foodReasonConsumption: ["Sarf", "Расход", "Consumption"],
  foodReasonAdjustment: ["Tuzatish", "Корректировка", "Adjustment"],
  foodReasonWaste: ["Yaroqsiz", "Списание", "Waste"],
  foodMealsTitle: ["Ovqatlar", "Блюда", "Meals"],
  foodMealsSub: [
    "Retseptlar va berilgan porsiyalar",
    "Рецепты и выданные порции",
    "Recipes and servings logged",
  ],
  foodAddMeal: ["Ovqat qo'shish", "Добавить блюдо", "Add meal"],
  foodIngredients: ["Ingredientlar", "Ингредиенты", "Ingredients"],
  foodAddIngredient: ["Ingredient qo'shish", "Добавить ингредиент", "Add ingredient"],
  foodPerServing: ["1 porsiyaga", "На 1 порцию", "Per serving"],
  foodServe: ["Berildi deb belgilash", "Отметить выдачу", "Log servings"],
  foodServeTitle: ["Porsiyalarni belgilash", "Отметить порции", "Log servings"],
  foodServings: ["Porsiya soni", "Число порций", "Servings"],
  foodNoStock: [
    "Omborda yetarli mahsulot yo'q",
    "Недостаточно продуктов на складе",
    "Not enough stock",
  ],
  foodReportTitle: ["Oziq-ovqat hisob-kitobi", "Отчёт по продуктам", "Food stock report"],
  foodReportSub: [
    "Davr bo'yicha kirim, chiqim va qoldiq",
    "Приход, расход и остаток за период",
    "Stock in, out and balance for the period",
  ],
  foodOpening: ["Boshlang'ich qoldiq", "Начальный остаток", "Opening"],
  foodStockIn: ["Kirim", "Приход", "Stock in"],
  foodStockOut: ["Chiqim", "Расход", "Stock out"],
  foodClosing: ["Yakuniy qoldiq", "Конечный остаток", "Closing"],
  foodValue: ["Qiymati", "Стоимость", "Value"],
  foodTotalValue: ["Jami qiymat", "Общая стоимость", "Total value"],

  setTitle: ["Sozlamalar", "Настройки", "Settings"],
  setSubtitle: [
    "Bog'cha profili va umumiy sozlamalar",
    "Профиль сада и общие настройки",
    "Kindergarten profile and general settings",
  ],
  setProfileSection: ["Bog'cha profili", "Профиль сада", "Kindergarten profile"],
  setName: ["Nomi", "Название", "Name"],
  setLegalName: ["Yuridik nomi", "Юридическое название", "Legal name"],
  setAddress: ["Manzil", "Адрес", "Address"],
  setHoursText: ["Ish vaqti", "Часы работы", "Working hours"],
  setAutoInvoiceDay: ["Oyning nechinchi kunida hisob-faktura yaratilsin", "В какой день месяца создавать счета", "Day of month to auto-generate invoices"],
  setSaved: ["Sozlamalar saqlandi", "Настройки сохранены", "Settings saved"],
  setSaveChanges: ["O'zgarishlarni saqlash", "Сохранить изменения", "Save changes"],
  setAutoInvoiceDayHint: [
    "Bo'sh qoldirilsa, hisob-fakturalar qo'lda yaratiladi",
    "Если оставить пустым, счета создаются вручную",
    "Leave empty to create invoices manually",
  ],
  setTariffs: ["Tariflar", "Тарифы", "Tariffs"],
  setTariffsSub: [
    "Guruh bo'yicha oylik to'lov",
    "Ежемесячная оплата по группам",
    "Monthly fee per group",
  ],
  setMonths: ["oy", "мес.", "months"],

  newLabel: ["Yangi", "Новый", "New"],
  whatAdd: ["Nima qo'shamiz?", "Что добавим?", "What would you like to add?"],
  quickPick: ["Tez tanlash", "Быстрый выбор", "Quick select"],
  thisMonth: ["Bu oy", "Этот месяц", "This month"],
  prevMonth: ["O'tgan oy", "Прошлый месяц", "Last month"],
  quarter: ["Chorak", "Квартал", "Quarter"],
  year: ["Yil", "Год", "Year"],
  markRead: [
    "Hammasini o'qilgan deb belgilash",
    "Отметить всё прочитанным",
    "Mark all as read",
  ],
  print: ["Chop etish", "Печать", "Print"],

  quickChildSub: [
    "Yangi bolani ro'yxatga olish",
    "Зарегистрировать нового ребёнка",
    "Register a new child",
  ],
  quickPaymentSub: ["Naqd yoki karta orqali", "Наличными или картой", "Cash or card"],
  quickExpenseSub: ["Kunlik sarf-xarajat", "Ежедневные расходы", "Daily spending"],
  quickStaffSub: ["Yangi ishchi", "Новый сотрудник", "New employee"],
  quickGroupSub: ["Yangi yosh guruhi", "Новая возрастная группа", "New age group"],
  quickMessageSub: [
    "Ommaviy Telegram xabari",
    "Массовое сообщение в Telegram",
    "Bulk Telegram message",
  ],

  groupMonthlyRevenue: ["Oylik daromad", "Доход в месяц", "Monthly revenue"],
  groupAgeYears: ["yosh", "лет", "yrs"],
};

function pick(key: string, idx: 0 | 1 | 2): string {
  const row = T[key];
  if (!row) throw new Error(`app-i18n: "${key}" kaliti topilmadi`);
  return row[idx];
}

function build(idx: 0 | 1 | 2): AppStrings {
  const p = (key: string) => pick(key, idx);
  return {
    search: p("search"),
    logout: p("logout"),
    privacy: p("privacy"),
    myProfile: p("myProfile"),
    language: p("language"),
    toggleTheme: p("toggleTheme"),
    collapseMenu: p("collapseMenu"),
    notifications: p("notifications"),
    noNotifications: p("noNotifications"),
    roleLabels: {
      OWNER: p("roleOwner"),
      MANAGER: p("roleManager"),
      TEACHER: p("roleTeacher"),
      PARENT: p("roleParent"),
    },
    nav: {
      sectionGeneral: p("navSectionGeneral"),
      sectionKindergarten: p("navSectionKindergarten"),
      sectionFinance: p("navSectionFinance"),
      sectionOther: p("navSectionOther"),
      myGroup: p("navMyGroup"),
      dashboard: p("navDashboard"),
      reports: p("navReports"),
      children: p("navChildren"),
      groups: p("navGroups"),
      attendance: p("navAttendance"),
      staff: p("navStaff"),
      payments: p("navPayments"),
      expenses: p("navExpenses"),
      parents: p("navParents"),
      settings: p("navSettings"),
    },
    common: {
      name: p("name"),
      fullName: p("fullName"),
      firstName: p("firstName"),
      lastName: p("lastName"),
      birthDate: p("birthDate"),
      guardians: p("guardians"),
      status: p("status"),
      active: p("active"),
      inactive: p("inactive"),
      capacity: p("capacity"),
      branch: p("branch"),
      role: p("role"),
      phone: p("phone"),
      email: p("email"),
      empty: p("empty"),
      save: p("save"),
      add: p("add"),
      edit: p("edit"),
      create: p("create"),
      cancel: p("cancel"),
      close: p("close"),
      saving: p("saving"),
      date: p("date"),
      period: p("period"),
      from: p("from"),
      to: p("to"),
      apply: p("apply"),
      search: p("commonSearch"),
      all: p("all"),
      loading: p("loading"),
      nothingFound: p("nothingFound"),
      nothingFoundSub: p("nothingFoundSub"),
      clearFilters: p("clearFilters"),
      errTitle: p("errTitle"),
      errSub: p("errSub"),
      retry: p("retry"),
      showing: p("showing"),
      of: p("of"),
      sum: p("sum"),
      mln: p("mln"),
      optional: p("optional"),
      required: p("required"),
      invalidPhone: p("invalidPhone"),
      invalidNumber: p("invalidNumber"),
      yes: p("yes"),
      no: p("no"),
      confirm: p("confirm"),
      deactivate: p("deactivate"),
      deactivateTitle: p("deactivateTitle"),
      reverse: p("reverse"),
      reverseTitle: p("reverseTitle"),
      reverseDone: p("reverseDone"),
      saved: p("saved"),
      view: p("view"),
      back: p("back"),
      next: p("next"),
      finish: p("finish"),
      reason: p("reason"),
      newLabel: p("newLabel"),
      whatAdd: p("whatAdd"),
      quickPick: p("quickPick"),
      thisMonth: p("thisMonth"),
      prevMonth: p("prevMonth"),
      quarter: p("quarter"),
      year: p("year"),
      markRead: p("markRead"),
      print: p("print"),
    },
    quick: {
      childSub: p("quickChildSub"),
      paymentSub: p("quickPaymentSub"),
      expenseSub: p("quickExpenseSub"),
      staffSub: p("quickStaffSub"),
      groupSub: p("quickGroupSub"),
      messageSub: p("quickMessageSub"),
    },
    dashboard: {
      title: p("dashTitle"),
      subtitle: p("dashSubtitle"),
      period: p("dashPeriod"),
      netProfit: p("dashNetProfit"),
      margin: p("dashMargin"),
      income: p("dashIncome"),
      outcome: p("dashOutcome"),
      breakeven: p("dashBreakeven"),
      aboveBreakeven: p("dashAboveBreakeven"),
      lastMonth: p("dashLastMonth"),
      biggest: p("dashBiggest"),
      payroll: p("dashPayroll"),
      todayAttendance: p("dashTodayAtt"),
      present: p("dashPresent"),
      sick: p("dashSick"),
      absent: p("dashAbsent"),
      debt: p("dashDebt"),
      families: p("dashFamilies"),
      over30: p("dashOver30"),
      chartTitle: p("dashChartTitle"),
      chartSub: p("dashChartSub"),
      expenseStructure: p("dashExpStructure"),
      agingTitle: p("dashAgingTitle"),
      agingSub: p("dashAgingSub"),
      notDue: p("dashNotDue"),
      aging1_30: p("dashAging1_30"),
      aging31_60: p("dashAging31_60"),
      aging60plus: p("dashAging60plus"),
      sendReminders: p("dashSendReminders"),
      unitTitle: p("dashUnitTitle"),
      unitSub: p("dashUnitSub"),
      uFee: p("dashUFee"),
      uVariable: p("dashUVariable"),
      uFixed: p("dashUFixed"),
      uMargin: p("dashUMargin"),
      uOther: p("dashUOther"),
      unitNote: p("dashUnitNote"),
      quickActions: p("dashQuickActions"),
      recentPayments: p("dashRecentPayments"),
      viewAll: p("dashViewAll"),
      method: p("dashMethod"),
      noBreakEven: p("dashNoBreakEven"),
      trendTitle: p("dashTrendTitle"),
      collectedLabel: p("dashCollectedLabel"),
    },
    children: {
      title: p("childrenTitle"),
      subtitle: p("childrenSubtitle"),
      addChild: p("addChild"),
      editChild: p("editChild"),
      aboutChild: p("aboutChild"),
      gender: p("gender"),
      boy: p("boy"),
      girl: p("girl"),
      medicalNotes: p("medicalNotes"),
      medicalHint: p("medicalHint"),
      group: p("group"),
      parent: p("parent"),
      guardianSection: p("guardianSection"),
      relation: p("relation"),
      rMother: p("rMother"),
      rFather: p("rFather"),
      rRelative: p("rRelative"),
      rOther: p("rOther"),
      canPickUp: p("canPickUp"),
      receivesNotifications: p("receivesNotifications"),
      financialTerms: p("financialTerms"),
      discount: p("discount"),
      discountNone: p("discountNone"),
      discountSibling: p("discountSibling"),
      discountStaffChild: p("discountStaffChild"),
      discountSocial: p("discountSocial"),
      discountOther: p("discountOther"),
      discountPercent: p("discountPercent"),
      startDate: p("startDate"),
      status: p("childStatus"),
      active: p("statusActive"),
      waiting: p("statusWaiting"),
      left: p("statusLeft"),
      filterActive: p("filterActive"),
      filterWaiting: p("filterWaiting"),
      filterLeft: p("filterLeft"),
      filterDebt: p("filterDebt"),
      transferGroup: p("transferGroup"),
      currentGroup: p("currentGroup"),
      newGroup: p("newGroup"),
      effectiveDate: p("effectiveDate"),
      transfer: p("transfer"),
      transferHint: p("transferHint"),
      transferDone: p("transferDone"),
      deactivateBody: p("deactivateChildBody"),
      savedChild: p("savedChild"),
      addGuardian: p("addGuardian"),
      guardianAdded: p("guardianAdded"),
      importTitle: p("importTitle"),
      importAction: p("importAction"),
      importUploadStep: p("importUploadStep"),
      importChooseFile: p("importChooseFile"),
      importPreviewStep: p("importPreviewStep"),
      importConfirmStep: p("importConfirmStep"),
      importRowNumber: p("importRowNumber"),
      importErrors: p("importErrors"),
      importValidRows: p("importValidRows"),
      importTotalRows: p("importTotalRows"),
      importGroup: p("importGroup"),
      importConfirmButton: p("importConfirmButton"),
      importDone: p("importDone"),
      importDryRunHint: p("importDryRunHint"),
    },
    groups: {
      title: p("groupsTitle"),
      subtitle: p("groupsSubtitle"),
      addGroup: p("addGroup"),
      editGroup: p("editGroup"),
      groupName: p("groupName"),
      ageRange: p("ageRange"),
      capacityField: p("capacityField"),
      monthlyFee: p("monthlyFee"),
      monthlyRevenue: p("groupMonthlyRevenue"),
      ageYears: p("groupAgeYears"),
      roomNumber: p("roomNumber"),
      mainTeacher: p("mainTeacher"),
      assignTeacher: p("assignTeacher"),
      occupancy: p("occupancy"),
      placesFree: p("placesFree"),
      full: p("full"),
      noTeacher: p("noTeacher"),
      deactivateBody: p("deactivateGroupBody"),
      savedGroup: p("savedGroup"),
      teacherAssigned: p("teacherAssigned"),
    },
    attendance: {
      title: p("attTitle"),
      subtitle: p("attSubtitle"),
      chooseGroup: p("attChooseGroup"),
      markAll: p("attMarkAll"),
      saveAndSend: p("attSaveAndSend"),
      saved: p("attSaved"),
      present: p("attPresent"),
      absent: p("attAbsent"),
      late: p("attLate"),
      excused: p("attExcused"),
      sick: p("attSick"),
      trend: p("attTrend"),
      trendSub: p("attTrendSub"),
      rate: p("attRate"),
    },
    payments: {
      title: p("payTitle"),
      subtitle: p("paySubtitle"),
      billed: p("payBilled"),
      collected: p("payCollected"),
      outstanding: p("payOutstanding"),
      progress: p("payProgress"),
      takePayment: p("payTakePayment"),
      newPayment: p("payNewPayment"),
      paymentMethod: p("payMethod"),
      cash: p("payCash"),
      card: p("payCard"),
      terminal: p("payTerminal"),
      bank: p("payBank"),
      other: p("payOther"),
      amount: p("payAmount"),
      prevDebt: p("payPrevDebt"),
      toPay: p("payToPay"),
      savePayment: p("paySavePayment"),
      paymentDone: p("payDone"),
      generateInvoices: p("payGenerateInvoices"),
      dueDate: p("payDueDate"),
      invoicesCreated: p("payInvoicesCreated"),
      invoicesSkipped: p("payInvoicesSkipped"),
      cancelInvoice: p("payCancelInvoice"),
      cancelDone: p("payCancelDone"),
      paid: p("payPaid"),
      partial: p("payPartial"),
      unpaid: p("payUnpaid"),
      filterPaid: p("payFilterPaid"),
      filterPartial: p("payFilterPartial"),
      filterUnpaid: p("payFilterUnpaid"),
      child: p("payChild"),
    },
    expenses: {
      title: p("expTitle"),
      subtitle: p("expSubtitle"),
      addExpense: p("addExpense"),
      category: p("category"),
      vendor: p("vendor"),
      description: p("description"),
      recurring: p("recurring"),
      manageCategories: p("manageCategories"),
      newCategory: p("newCategory"),
      categoryName: p("categoryName"),
      variableFlag: p("variableFlag"),
      variableHint: p("variableHint"),
      total: p("expTotal"),
      byCategory: p("expByCategory"),
    },
    staff: {
      title: p("staffTitle"),
      subtitle: p("staffSubtitle"),
      addStaff: p("addStaff"),
      editStaff: p("editStaff"),
      position: p("position"),
      salary: p("salary"),
      hireDate: p("hireDate"),
      employmentType: p("employmentType"),
      fullTime: p("fullTime"),
      partTime: p("partTime"),
      hourly: p("hourly"),
      passportNumber: p("passportNumber"),
      payrollFund: p("payrollFund"),
      personalInfo: p("personalInfo"),
      workInfo: p("workInfo"),
      accessInfo: p("accessInfo"),
      login: p("staffLogin"),
      password: p("staffPassword"),
      savedStaff: p("savedStaff"),
      deactivateBody: p("deactivateStaffBody"),
      filterAll: p("staffFilterAll"),
      payrollRunTitle: p("payrollRunTitle"),
      payrollRunAction: p("payrollRunAction"),
      baseSalary: p("baseSalary"),
      bonus: p("bonus"),
      deduction: p("deduction"),
      advanceDeducted: p("advanceDeducted"),
      netPay: p("netPay"),
      payrollHistory: p("payrollHistory"),
      payrollPeriod: p("payrollPeriod"),
      payrollStatus: p("payrollStatus"),
      payrollRecorded: p("payrollRecorded"),
      payrollReversed: p("payrollReversed"),
      payrollPaidAt: p("payrollPaidAt"),
      payrollSaved: p("payrollSaved"),
      payrollReverseConfirm: p("payrollReverseConfirm"),
    },
    reports: {
      title: p("repTitle"),
      subtitle: p("repSubtitle"),
      plTitle: p("repPlTitle"),
      revenueSection: p("repRevenueSection"),
      expenseSection: p("repExpenseSection"),
      totalRevenue: p("repTotalRevenue"),
      totalExpenses: p("repTotalExpenses"),
      netTotal: p("repNetTotal"),
      readyReports: p("repReadyReports"),
      repPl: p("repPlFile"),
      repRevenueByGroup: p("repRevenueByGroup"),
      repExpenses: p("repExpensesFile"),
      downloadCsv: p("repDownloadCsv"),
      revenue: p("repRevenue"),
      expensesTotal: p("repExpensesTotal"),
      net: p("repNet"),
      revenueByGroup: p("repRevenueByGroup"),
    },
    pages: {
      children: p("pageChildren"),
      groups: p("pageGroups"),
      billing: p("pageBilling"),
      staff: p("pageStaff"),
      chooseChild: p("chooseChild"),
      chooseBranch: p("chooseBranch"),
      chooseGroup: p("chooseGroup"),
    },
    messaging: {
      title: p("msgTitle"),
      subtitle: p("msgSubtitle"),
      connectedFamilies: p("msgConnectedFamilies"),
      sentThisMonth: p("msgSentThisMonth"),
      autoNotifications: p("msgAutoNotifications"),
      notifChildCheckedIn: p("msgNotifChildCheckedIn"),
      notifChildSick: p("msgNotifChildSick"),
      notifPaymentReminder: p("msgNotifPaymentReminder"),
      notifDebtWarning: p("msgNotifDebtWarning"),
      notifBirthdayGreeting: p("msgNotifBirthdayGreeting"),
      broadcastTitle: p("msgBroadcastTitle"),
      audience: p("msgAudience"),
      audienceAll: p("msgAudienceAll"),
      audienceGroup: p("msgAudienceGroup"),
      audienceDebtors: p("msgAudienceDebtors"),
      messageText: p("msgMessageText"),
      send: p("msgSend"),
      sent: p("msgSent"),
      queuedCount: p("msgQueuedCount"),
      parentsListTitle: p("msgParentsListTitle"),
      messagesUnit: p("msgMessagesUnit"),
      autoNotificationsSub: p("msgAutoNotificationsSub"),
      broadcastSub: p("msgBroadcastSub"),
      messagePlaceholder: p("msgMessagePlaceholder"),
      sendHint: p("msgSendHint"),
      hintCheckedIn: p("msgHintCheckedIn"),
      hintSick: p("msgHintSick"),
      hintPaymentReminder: p("msgHintPaymentReminder"),
      hintDebtWarning: p("msgHintDebtWarning"),
      hintBirthday: p("msgHintBirthday"),
      inviteGet: p("msgInviteGet"),
      inviteTitle: p("msgInviteTitle"),
      inviteSubtitle: p("msgInviteSubtitle"),
      inviteSteps: p("msgInviteSteps"),
      inviteExpires: p("msgInviteExpires"),
      inviteCopy: p("msgInviteCopy"),
      inviteCopied: p("msgInviteCopied"),
      inviteAlreadyLinked: p("msgInviteAlreadyLinked"),
    },
    food: {
      productsTitle: p("foodProductsTitle"),
      productsSub: p("foodProductsSub"),
      addProduct: p("foodAddProduct"),
      unit: p("foodUnit"),
      unitCost: p("foodUnitCost"),
      stock: p("foodStock"),
      stockMovement: p("foodStockMovement"),
      movementIn: p("foodMovementIn"),
      movementOut: p("foodMovementOut"),
      quantity: p("foodQuantity"),
      reason: p("foodReason"),
      reasonPurchase: p("foodReasonPurchase"),
      reasonConsumption: p("foodReasonConsumption"),
      reasonAdjustment: p("foodReasonAdjustment"),
      reasonWaste: p("foodReasonWaste"),
      mealsTitle: p("foodMealsTitle"),
      mealsSub: p("foodMealsSub"),
      addMeal: p("foodAddMeal"),
      ingredients: p("foodIngredients"),
      addIngredient: p("foodAddIngredient"),
      perServing: p("foodPerServing"),
      serve: p("foodServe"),
      serveTitle: p("foodServeTitle"),
      servings: p("foodServings"),
      noStock: p("foodNoStock"),
      reportTitle: p("foodReportTitle"),
      reportSub: p("foodReportSub"),
      opening: p("foodOpening"),
      stockIn: p("foodStockIn"),
      stockOut: p("foodStockOut"),
      closing: p("foodClosing"),
      value: p("foodValue"),
      totalValue: p("foodTotalValue"),
    },
    settings: {
      title: p("setTitle"),
      subtitle: p("setSubtitle"),
      profileSection: p("setProfileSection"),
      name: p("setName"),
      legalName: p("setLegalName"),
      address: p("setAddress"),
      hoursText: p("setHoursText"),
      autoInvoiceDay: p("setAutoInvoiceDay"),
      autoInvoiceDayHint: p("setAutoInvoiceDayHint"),
      saved: p("setSaved"),
      saveChanges: p("setSaveChanges"),
      tariffs: p("setTariffs"),
      tariffsSub: p("setTariffsSub"),
      months: p("setMonths"),
    },
  };
}

export const APP_I18N: Record<Lang, AppStrings> = {
  uz: build(0),
  ru: build(1),
  en: build(2),
};
