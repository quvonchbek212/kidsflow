// Backend API klienti. Backendning OpenAPI sxemasi asosida (8-bo'lim) — MVP uchun
// qo'lda yozilgan typed client. Keyinchalik `openapi-typescript` bilan generatsiya
// qilinishi mumkin.

import { clearTokens, getRefreshToken, getToken, setTokens } from "./auth";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  auth?: boolean;
}

// --- Access token yangilash (rotation) ---
//
// Access token 15 daqiqada tugaydi, refresh token esa 30 kun yashaydi. 401
// kelganda refresh token bilan yangi juftlikni olamiz va so'rovni bir marta
// qaytaramiz — foydalanuvchi har 15 daqiqada login sahifasiga tushmasligi uchun.

let refreshPromise: Promise<boolean> | null = null;

async function requestNewTokens(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
    cache: "no-store",
  });
  if (!response.ok) return false;

  const tokens = (await response.json()) as TokenResponse;
  setTokens({
    accessToken: tokens.access_token,
    refreshToken: tokens.refresh_token,
  });
  return true;
}

// Backend refresh tokenni rotation qiladi (eskisi bekor bo'ladi), shuning uchun
// bir vaqtda ketayotgan bir nechta 401 bitta yangilash so'roviga birlashtiriladi.
function ensureRefreshed(): Promise<boolean> {
  if (refreshPromise === null) {
    refreshPromise = requestNewTokens()
      .catch(() => false)
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

async function request<T>(
  path: string,
  options: RequestOptions = {},
  allowRetry = true,
): Promise<T> {
  const { method = "GET", body, auth = true } = options;
  const headers: Record<string, string> = { "Content-Type": "application/json" };

  if (auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });

  if (response.status === 401) {
    // Tokensiz so'rovlarda (login, parolni tiklash) 401 "sessiya tugadi" degani
    // emas — backend xabarini ("Login yoki parol noto'g'ri.") o'zgartirmay uzatamiz.
    if (!auth) {
      throw new ApiError(401, await extractDetail(response));
    }
    if (allowRetry && (await ensureRefreshed())) {
      return request<T>(path, options, false);
    }
    clearTokens();
    throw new ApiError(401, "Avtorizatsiya talab qilinadi.");
  }
  if (!response.ok) {
    throw new ApiError(response.status, await extractDetail(response));
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

async function requestForm<T>(
  path: string,
  form: FormData,
  allowRetry = true,
): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers,
    body: form,
    cache: "no-store",
  });

  if (response.status === 401) {
    if (allowRetry && (await ensureRefreshed())) {
      return requestForm<T>(path, form, false);
    }
    clearTokens();
    throw new ApiError(401, "Avtorizatsiya talab qilinadi.");
  }
  if (!response.ok) {
    throw new ApiError(response.status, await extractDetail(response));
  }
  return (await response.json()) as T;
}

async function extractDetail(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") return body.detail;
  } catch {
    // ignore
  }
  return "So'rovni bajarib bo'lmadi.";
}

// --- Turlar: auth / umumiy ---

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface RoleGrant {
  role: string;
  branch_id: string | null;
}

export interface CurrentUser {
  id: string;
  full_name: string;
  username: string | null;
  phone: string | null;
  email: string | null;
  roles: RoleGrant[];
}

export interface Branch {
  id: string;
  name: string;
  address: string | null;
  phone: string | null;
  capacity: number | null;
  is_active: boolean;
}

// --- Turlar: bolalar ---

export type ChildStatus = "active" | "waiting" | "left";

export interface Child {
  id: string;
  full_name: string;
  birth_date: string;
  gender: string | null;
  medical_notes: string | null;
  is_active: boolean;
  status: ChildStatus;
  guardians: {
    guardian_user_id: string;
    full_name: string;
    relationship_type: string;
    is_primary: boolean;
  }[];
}

export type DiscountType = "NONE" | "SIBLING" | "STAFF_CHILD" | "SOCIAL" | "OTHER";

export interface Enrollment {
  id: string;
  child_id: string;
  branch_id: string;
  group_id: string;
  start_date: string;
  end_date: string | null;
  status: string;
  notes: string | null;
  discount_type: DiscountType | null;
  discount_percent: string | null;
}

export interface ParentRow {
  id: string;
  full_name: string;
  phone: string | null;
  email: string | null;
  telegram_linked: boolean;
  children_names: string[];
}

export interface InvitationCode {
  code: string;
  user_id: string;
  expires_at: string;
}

// --- Turlar: kunlik hisobot (4.4-bo'lim) ---

export type MealStatus = "ATE_WELL" | "ATE_SOME" | "REFUSED";
export type Mood = "HAPPY" | "CALM" | "TIRED" | "SAD" | "SICK";

export interface DailyReport {
  id: string;
  branch_id: string;
  child_id: string;
  report_date: string;
  meal_status: MealStatus | null;
  nap_minutes: number | null;
  mood: Mood | null;
  activities_text: string | null;
  teacher_note: string | null;
  final_summary: string | null;
  is_published: boolean;
  published_at: string | null;
  files: { file_id: string; original_name: string; content_type: string }[];
}

export interface DailyReportRosterRow {
  child_id: string;
  child_name: string;
  report: DailyReport | null;
}

export interface DailyReportInput {
  meal_status?: MealStatus | null;
  nap_minutes?: number | null;
  mood?: Mood | null;
  activities_text?: string | null;
  teacher_note?: string | null;
  final_summary?: string | null;
}

export interface Group {
  id: string;
  branch_id: string;
  name: string;
  min_age_months: number | null;
  max_age_months: number | null;
  capacity: number;
  is_active: boolean;
  monthly_fee: string | null;
  room_number: string | null;
  teachers: { teacher_user_id: string; is_primary: boolean }[];
}

export interface AttendanceRosterRow {
  child_id: string;
  child_name: string;
  status: string | null;
  check_in_at: string | null;
  check_out_at: string | null;
}

// --- Turlar: xodimlar / kadrlar ---

export type EmploymentType = "FULL_TIME" | "PART_TIME" | "HOURLY";

export interface StaffUser {
  id: string;
  full_name: string;
  username: string | null;
  phone: string | null;
  email: string | null;
  is_active: boolean;
  position: string | null;
  monthly_salary: string | null;
  birth_date: string | null;
  passport_number: string | null;
  hire_date: string | null;
  employment_type: EmploymentType | null;
  roles: RoleGrant[];
}

export interface PayrollStaffRow {
  id: string;
  full_name: string;
  position: string | null;
  role: string;
  monthly_salary: string;
}

export interface PayrollSummary {
  total_fund: string;
  staff: PayrollStaffRow[];
}

// --- Turlar: moliya ---

export interface Invoice {
  id: string;
  branch_id: string;
  child_id: string;
  billing_period: string;
  due_date: string;
  original_amount: string;
  adjusted_amount: string;
  paid_amount: string;
  outstanding_amount: string;
  status: string;
}

export interface FeePlan {
  id: string;
  branch_id: string;
  name: string;
  monthly_amount: string;
  currency: string;
  is_active: boolean;
}

export interface ExpenseCategory {
  id: string;
  name: string;
  is_system: boolean;
  is_active: boolean;
  is_variable: boolean;
}

export interface Expense {
  id: string;
  branch_id: string;
  category_id: string;
  amount: string;
  expense_date: string;
  vendor: string | null;
  description: string | null;
  status: string;
  is_recurring: boolean;
}

export interface DebtAgingBucket {
  label: "not_due" | "aging_1_30" | "aging_31_60" | "aging_60_plus";
  total: string;
}

export interface GroupRevenueRow {
  group_id: string;
  total: string;
}

export interface CategoryExpenseRow {
  category_id: string;
  category_name: string;
  total: string;
  is_variable: boolean;
}

export interface BreakEvenSummary {
  active_children: number;
  fixed_costs: string;
  variable_costs: string;
  fee_per_child: string;
  variable_cost_per_child: string;
  contribution_margin: string;
  contribution_margin_ratio: string;
  breakeven_revenue: string;
  breakeven_children: number;
}

export interface FinanceDashboard {
  period_start: string;
  period_end: string;
  accrual_revenue: string;
  cash_collected: string;
  outstanding: string;
  expenses: string;
  net_cash: string;
  branches: {
    branch_id: string;
    accrual_revenue: string;
    cash_collected: string;
    outstanding: string;
    expenses: string;
    net_cash: string;
  }[];
  aging: DebtAgingBucket[];
  revenue_by_group: GroupRevenueRow[];
  expenses_by_category: CategoryExpenseRow[];
  break_even: BreakEvenSummary | null;
}

export interface PaymentAllocationOut {
  invoice_id: string;
  amount: string;
}

export interface Payment {
  id: string;
  branch_id: string;
  child_id: string;
  amount: string;
  payment_method: string;
  paid_at: string;
  status: string;
  allocations: PaymentAllocationOut[];
  unallocated_amount: string;
}

export interface AttendanceTrendPoint {
  attendance_date: string;
  present_count: number;
  total_count: number;
}

export interface AttendanceTrend {
  group_id: string;
  points: AttendanceTrendPoint[];
}

// --- Turlar: oziq-ovqat / oshxona ---

export interface FoodProduct {
  id: string;
  branch_id: string;
  name: string;
  unit: string;
  unit_cost: string | null;
  current_stock: string;
  is_active: boolean;
}

export interface MealIngredient {
  product_id: string;
  quantity_per_serving: string;
}

export interface Meal {
  id: string;
  branch_id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  ingredients: MealIngredient[];
}

export interface StockReportRow {
  product_id: string;
  product_name: string;
  unit: string;
  opening_stock: string;
  stock_in: string;
  stock_out: string;
  closing_stock: string;
  unit_cost: string | null;
  closing_value: string;
}

export interface StockReport {
  branch_id: string;
  period_start: string;
  period_end: string;
  rows: StockReportRow[];
  total_value: string;
}

// --- Turlar: payroll ---

export interface PayrollRun {
  id: string;
  branch_id: string;
  user_id: string;
  period: string;
  base_salary: string;
  bonus: string;
  deduction: string;
  advance_deducted: string;
  net_pay: string;
  status: string;
  expense_id: string | null;
  paid_at: string;
}

// --- Turlar: sozlamalar ---

export interface KindergartenSettings {
  id: string;
  name: string;
  legal_name: string | null;
  address: string | null;
  phone: string | null;
  timezone: string;
  default_language: string;
  currency: string;
  hours_text: string | null;
  auto_invoice_day: number | null;
  notification_toggles: Record<string, boolean>;
}

// --- Turlar: xabar yuborish ---

export type BroadcastAudience = "all" | "group" | "debtors";

export interface MessagingStats {
  connected_families: number;
  sent_this_month: number;
}

// --- Turlar: Excel/CSV import ---

export interface ImportPreviewRow {
  row_number: number;
  full_name: string | null;
  birth_date: string | null;
  guardian_name: string | null;
  guardian_phone: string | null;
  errors: string[];
  valid: boolean;
}

export interface ImportResult {
  dry_run: boolean;
  total_rows: number;
  valid_rows: number;
  imported: number;
  rows: ImportPreviewRow[];
}

// --- API ---

export const api = {
  // --- auth ---
  async login(login: string, password: string): Promise<TokenResponse> {
    return request<TokenResponse>("/auth/login", {
      method: "POST",
      body: { login, password },
      auth: false,
    });
  },

  me(): Promise<CurrentUser> {
    return request<CurrentUser>("/auth/me");
  },

  // Refresh tokenni serverda ham bekor qiladi — faqat localStorage tozalansa,
  // token 30 kun davomida amal qilaverardi.
  async logout(): Promise<void> {
    const refreshToken = getRefreshToken();
    try {
      if (refreshToken) {
        await request("/auth/logout", {
          method: "POST",
          body: { refresh_token: refreshToken },
          auth: false,
        });
      }
    } catch {
      // Tarmoq xatosi chiqishga to'sqinlik qilmasin.
    } finally {
      clearTokens();
    }
  },

  forgotPassword(email: string): Promise<unknown> {
    return request("/auth/forgot-password", {
      method: "POST",
      body: { email },
      auth: false,
    });
  },

  resetPassword(token: string, newPassword: string): Promise<unknown> {
    return request("/auth/reset-password", {
      method: "POST",
      body: { token, new_password: newPassword },
      auth: false,
    });
  },

  listBranches(): Promise<Branch[]> {
    return request<Branch[]>("/branches");
  },

  // --- bolalar ---
  listChildren(): Promise<Child[]> {
    return request<Child[]>("/children");
  },

  getChild(childId: string): Promise<Child> {
    return request<Child>(`/children/${childId}`);
  },

  createChild(body: {
    full_name: string;
    birth_date: string;
    gender?: string;
    medical_notes?: string;
  }): Promise<Child> {
    return request<Child>("/children", { method: "POST", body });
  },

  updateChild(
    childId: string,
    body: Partial<{
      full_name: string;
      birth_date: string;
      gender: string | null;
      medical_notes: string | null;
      is_active: boolean;
    }>,
  ): Promise<Child> {
    return request<Child>(`/children/${childId}`, { method: "PATCH", body });
  },

  addGuardian(
    childId: string,
    body: {
      full_name: string;
      phone?: string;
      email?: string;
      relationship_type: string;
      is_primary?: boolean;
      can_pick_up?: boolean;
      receives_notifications?: boolean;
    },
  ): Promise<{ guardian_user_id: string; child_id: string; relationship_type: string }> {
    return request(`/children/${childId}/guardians`, { method: "POST", body });
  },

  createEnrollment(
    childId: string,
    body: {
      branch_id: string;
      group_id: string;
      start_date: string;
      status?: string;
      notes?: string;
      discount_type?: DiscountType;
      discount_percent?: string;
    },
  ): Promise<Enrollment> {
    return request<Enrollment>(`/children/${childId}/enrollments`, {
      method: "POST",
      body,
    });
  },

  updateEnrollment(
    enrollmentId: string,
    body: Partial<{
      status: string;
      end_date: string;
      group_id: string;
      notes: string;
      discount_type: DiscountType;
      discount_percent: string;
    }>,
  ): Promise<Enrollment> {
    return request<Enrollment>(`/enrollments/${enrollmentId}`, {
      method: "PATCH",
      body,
    });
  },

  transferChild(
    childId: string,
    body: {
      new_group_id: string;
      effective_date: string;
      reason?: string;
      discount_type?: DiscountType;
      discount_percent?: string;
    },
  ): Promise<Enrollment> {
    return request<Enrollment>(`/children/${childId}/transfer`, {
      method: "POST",
      body,
    });
  },

  listParents(): Promise<ParentRow[]> {
    return request<ParentRow[]>("/children/parents");
  },

  // Ota-onani Telegram botga ulash uchun bir martalik kod. Kod ota-onaga
  // og'zaki/qo'lda beriladi — u botga yuborgach hisob bog'lanadi.
  createInvitation(userId: string): Promise<InvitationCode> {
    return request<InvitationCode>("/telegram/invitations", {
      method: "POST",
      body: { user_id: userId },
    });
  },

  listGroups(): Promise<Group[]> {
    return request<Group[]>("/groups");
  },

  // --- kunlik hisobot ---
  dailyReportRoster(groupId: string, date: string): Promise<DailyReportRosterRow[]> {
    const params = new URLSearchParams({ group_id: groupId, date });
    return request<DailyReportRosterRow[]>(`/daily-reports/roster?${params.toString()}`);
  },

  createDailyReport(
    childId: string,
    reportDate: string,
    input: DailyReportInput,
  ): Promise<DailyReport> {
    return request<DailyReport>("/daily-reports", {
      method: "POST",
      body: { child_id: childId, report_date: reportDate, ...input },
    });
  },

  updateDailyReport(reportId: string, input: DailyReportInput): Promise<DailyReport> {
    return request<DailyReport>(`/daily-reports/${reportId}`, {
      method: "PATCH",
      body: input,
    });
  },

  // E'lon qilingandan keyin hisobot tahrirlanmaydi va ota-onaga outbox orqali
  // Telegram bildirishnomasi ketadi (9-bo'lim).
  publishDailyReport(reportId: string): Promise<DailyReport> {
    return request<DailyReport>(`/daily-reports/${reportId}/publish`, {
      method: "POST",
    });
  },

  createGroup(body: {
    branch_id: string;
    name: string;
    min_age_months?: number;
    max_age_months?: number;
    capacity?: number;
    monthly_fee?: string;
    room_number?: string;
  }): Promise<Group> {
    return request<Group>("/groups", { method: "POST", body });
  },

  updateGroup(
    groupId: string,
    body: Partial<{
      name: string;
      min_age_months: number;
      max_age_months: number;
      capacity: number;
      is_active: boolean;
      monthly_fee: string;
      room_number: string;
    }>,
  ): Promise<Group> {
    return request<Group>(`/groups/${groupId}`, { method: "PATCH", body });
  },

  assignTeacher(
    groupId: string,
    teacherUserId: string,
    isPrimary = false,
  ): Promise<unknown> {
    return request(`/groups/${groupId}/teachers`, {
      method: "POST",
      body: { teacher_user_id: teacherUserId, is_primary: isPrimary },
    });
  },

  attendanceRoster(groupId: string, date: string): Promise<AttendanceRosterRow[]> {
    const params = new URLSearchParams({ group_id: groupId, date });
    return request<AttendanceRosterRow[]>(`/attendance/roster?${params.toString()}`);
  },

  markAttendance(body: {
    child_id: string;
    attendance_date: string;
    status: string;
  }): Promise<unknown> {
    return request("/attendance", { method: "POST", body });
  },

  markAttendanceBulk(body: {
    group_id: string;
    attendance_date: string;
    entries: { child_id: string; status: string; note?: string }[];
  }): Promise<unknown> {
    return request("/attendance/bulk", { method: "POST", body });
  },

  attendanceTrend(groupId: string, days = 11): Promise<AttendanceTrend> {
    const params = new URLSearchParams({ group_id: groupId, days: String(days) });
    return request<AttendanceTrend>(`/attendance/trend?${params.toString()}`);
  },

  // --- kadrlar / xodimlar ---
  listStaff(position?: string): Promise<StaffUser[]> {
    const qs = position ? `?position=${encodeURIComponent(position)}` : "";
    return request<StaffUser[]>(`/users${qs}`);
  },

  createStaff(body: {
    full_name: string;
    username: string;
    phone?: string;
    email?: string;
    password: string;
    role: string;
    position?: string;
    branch_id?: string;
    monthly_salary?: string;
    birth_date?: string;
    passport_number?: string;
    hire_date?: string;
    employment_type?: EmploymentType;
  }): Promise<StaffUser> {
    return request<StaffUser>("/users", { method: "POST", body });
  },

  updateStaff(
    userId: string,
    body: Partial<{
      full_name: string;
      phone: string;
      email: string;
      position: string;
      monthly_salary: string;
      birth_date: string;
      passport_number: string;
      hire_date: string;
      employment_type: EmploymentType;
      is_active: boolean;
    }>,
  ): Promise<StaffUser> {
    return request<StaffUser>(`/users/${userId}`, { method: "PATCH", body });
  },

  updateSalary(userId: string, monthlySalary: string): Promise<StaffUser> {
    return request<StaffUser>(`/users/${userId}/salary`, {
      method: "PATCH",
      body: { monthly_salary: monthlySalary },
    });
  },

  payrollSummary(): Promise<PayrollSummary> {
    return request<PayrollSummary>("/users/payroll-summary");
  },

  // --- moliya ---
  childInvoices(childId: string): Promise<Invoice[]> {
    return request<Invoice[]>(`/children/${childId}/invoices`);
  },

  branchInvoices(branchId: string, billingPeriod: string): Promise<Invoice[]> {
    const params = new URLSearchParams({
      branch_id: branchId,
      billing_period: billingPeriod,
    });
    return request<Invoice[]>(`/invoices?${params.toString()}`);
  },

  generateInvoices(
    branchId: string,
    billingPeriod: string,
    feePlanId?: string,
    dueDay?: number,
  ): Promise<{ created: number; skipped: number; billing_period: string }> {
    return request("/invoices/generate", {
      method: "POST",
      body: {
        branch_id: branchId,
        billing_period: billingPeriod,
        fee_plan_id: feePlanId,
        due_day: dueDay,
      },
    });
  },

  addInvoiceAdjustment(
    invoiceId: string,
    body: { adjustment_type: "DISCOUNT" | "SURCHARGE" | "WRITE_OFF"; amount: string; reason?: string },
  ): Promise<Invoice> {
    return request<Invoice>(`/invoices/${invoiceId}/adjustments`, {
      method: "POST",
      body,
    });
  },

  cancelInvoice(invoiceId: string): Promise<Invoice> {
    return request<Invoice>(`/invoices/${invoiceId}/cancel`, { method: "POST" });
  },

  recordPayment(body: {
    child_id: string;
    amount: string;
    payment_method: string;
    paid_at: string;
    reference?: string;
    idempotency_key?: string;
  }): Promise<Payment> {
    return request<Payment>("/payments", { method: "POST", body });
  },

  reversePayment(paymentId: string): Promise<Payment> {
    return request<Payment>(`/payments/${paymentId}/reverse`, { method: "POST" });
  },

  listFeePlans(): Promise<FeePlan[]> {
    return request<FeePlan[]>("/fee-plans");
  },

  createFeePlan(body: {
    branch_id: string;
    name: string;
    monthly_amount: string;
  }): Promise<FeePlan> {
    return request<FeePlan>("/fee-plans", { method: "POST", body });
  },

  listExpenseCategories(): Promise<ExpenseCategory[]> {
    return request<ExpenseCategory[]>("/expense-categories");
  },

  createExpenseCategory(body: {
    name: string;
    is_variable?: boolean;
  }): Promise<ExpenseCategory> {
    return request<ExpenseCategory>("/expense-categories", { method: "POST", body });
  },

  updateExpenseCategory(
    categoryId: string,
    body: Partial<{ name: string; is_variable: boolean; is_active: boolean }>,
  ): Promise<ExpenseCategory> {
    return request<ExpenseCategory>(`/expense-categories/${categoryId}`, {
      method: "PATCH",
      body,
    });
  },

  listExpenses(
    branchId: string,
    periodStart?: string,
    periodEnd?: string,
  ): Promise<Expense[]> {
    const params = new URLSearchParams({ branch_id: branchId });
    if (periodStart) params.set("period_start", periodStart);
    if (periodEnd) params.set("period_end", periodEnd);
    return request<Expense[]>(`/expenses?${params.toString()}`);
  },

  createExpense(body: {
    branch_id: string;
    category_id: string;
    amount: string;
    expense_date: string;
    vendor?: string;
    description?: string;
    is_recurring?: boolean;
  }): Promise<Expense> {
    return request<Expense>("/expenses", { method: "POST", body });
  },

  reverseExpense(expenseId: string): Promise<Expense> {
    return request<Expense>(`/expenses/${expenseId}/reverse`, { method: "POST" });
  },

  dashboard(periodStart: string, periodEnd: string): Promise<FinanceDashboard> {
    const params = new URLSearchParams({
      period_start: periodStart,
      period_end: periodEnd,
    });
    return request<FinanceDashboard>(`/analytics/dashboard?${params.toString()}`);
  },

  // --- oziq-ovqat / oshxona ---
  listFoodProducts(branchId: string): Promise<FoodProduct[]> {
    const params = new URLSearchParams({ branch_id: branchId });
    return request<FoodProduct[]>(`/food/products?${params.toString()}`);
  },

  createFoodProduct(body: {
    branch_id: string;
    name: string;
    unit: string;
    unit_cost?: string;
  }): Promise<FoodProduct> {
    return request<FoodProduct>("/food/products", { method: "POST", body });
  },

  recordStockMovement(body: {
    product_id: string;
    movement_type: "IN" | "OUT";
    quantity: string;
    reason: string;
    note?: string;
  }): Promise<unknown> {
    return request("/food/stock-movements", { method: "POST", body });
  },

  listMeals(branchId: string): Promise<Meal[]> {
    const params = new URLSearchParams({ branch_id: branchId });
    return request<Meal[]>(`/food/meals?${params.toString()}`);
  },

  createMeal(body: {
    branch_id: string;
    name: string;
    description?: string;
    ingredients: MealIngredient[];
  }): Promise<Meal> {
    return request<Meal>("/food/meals", { method: "POST", body });
  },

  logMeal(body: {
    meal_id: string;
    serving_date: string;
    servings_count: number;
  }): Promise<unknown> {
    return request("/food/meal-logs", { method: "POST", body });
  },

  stockReport(
    branchId: string,
    periodStart: string,
    periodEnd: string,
  ): Promise<StockReport> {
    const params = new URLSearchParams({
      branch_id: branchId,
      period_start: periodStart,
      period_end: periodEnd,
    });
    return request<StockReport>(`/food/stock-report?${params.toString()}`);
  },

  // --- payroll ---
  createPayrollRun(body: {
    branch_id: string;
    user_id: string;
    period: string;
    base_salary?: string;
    bonus?: string;
    deduction?: string;
    advance_deducted?: string;
    paid_at: string;
  }): Promise<PayrollRun> {
    return request<PayrollRun>("/payroll/runs", { method: "POST", body });
  },

  listPayrollRuns(params: {
    user_id?: string;
    branch_id?: string;
    period?: string;
  }): Promise<PayrollRun[]> {
    const qs = new URLSearchParams();
    if (params.user_id) qs.set("user_id", params.user_id);
    if (params.branch_id) qs.set("branch_id", params.branch_id);
    if (params.period) qs.set("period", params.period);
    const query = qs.toString();
    return request<PayrollRun[]>(`/payroll/runs${query ? `?${query}` : ""}`);
  },

  reversePayrollRun(runId: string): Promise<PayrollRun> {
    return request<PayrollRun>(`/payroll/runs/${runId}/reverse`, { method: "POST" });
  },

  // --- sozlamalar ---
  getSettings(): Promise<KindergartenSettings> {
    return request<KindergartenSettings>("/settings");
  },

  updateSettings(
    body: Partial<{
      name: string;
      legal_name: string;
      address: string;
      phone: string;
      hours_text: string;
      auto_invoice_day: number;
      notification_toggles: Record<string, boolean>;
    }>,
  ): Promise<KindergartenSettings> {
    return request<KindergartenSettings>("/settings", { method: "PATCH", body });
  },

  // --- xabar yuborish ---
  broadcastMessage(body: {
    branch_id: string;
    audience: BroadcastAudience;
    group_id?: string;
    text: string;
  }): Promise<{ queued_count: number }> {
    return request("/messages/broadcast", { method: "POST", body });
  },

  messagingStats(branchId: string): Promise<MessagingStats> {
    const params = new URLSearchParams({ branch_id: branchId });
    return request<MessagingStats>(`/messages/stats?${params.toString()}`);
  },

  // --- Excel/CSV import ---
  importChildren(
    branchId: string,
    groupId: string,
    dryRun: boolean,
    file: File,
  ): Promise<ImportResult> {
    const form = new FormData();
    form.set("branch_id", branchId);
    form.set("group_id", groupId);
    form.set("dry_run", String(dryRun));
    form.set("upload", file);
    return requestForm<ImportResult>("/children/import", form);
  },
};

export { API_BASE_URL };
