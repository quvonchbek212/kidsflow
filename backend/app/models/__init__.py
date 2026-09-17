"""ORM modellar paketi.

Barcha modellar shu yerda import qilinadi, shunda `Base.metadata` to'liq bo'ladi
(Alembic autogenerate va testdagi create_all uchun zarur).
"""

from app.models.ai import AIUsageLog, KnowledgeDocument
from app.models.attendance import Attendance
from app.models.audit import AuditLog
from app.models.child import Child, ChildGuardian
from app.models.daily_report import DailyReport, DailyReportFile
from app.models.enrollment import Enrollment
from app.models.enums import (
    AdjustmentType,
    AIFeature,
    AttendanceStatus,
    EnrollmentStatus,
    ExpenseStatus,
    FileScanStatus,
    Gender,
    GuardianRelationship,
    InvoiceStatus,
    KnowledgeCategory,
    MealStatus,
    MessageDirection,
    Mood,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
    OutboxStatus,
    PaymentMethod,
    PaymentStatus,
    PayrollStatus,
    Role,
    StaffPosition,
    StockMovementReason,
    StockMovementType,
)
from app.models.file import File
from app.models.finance import (
    Expense,
    ExpenseCategory,
    FeePlan,
    Invoice,
    InvoiceAdjustment,
    PaymentAllocation,
    PaymentTransaction,
)
from app.models.food import (
    FoodProduct,
    FoodStockMovement,
    Meal,
    MealIngredient,
    MealLog,
)
from app.models.group import Group, GroupTeacher
from app.models.invitation import TelegramInvitation
from app.models.messaging import (
    BranchNotificationSettings,
    DailyJobRun,
    Notification,
    OutboxEvent,
    ParentMessage,
)
from app.models.organization import Branch, KindergartenSettings
from app.models.payroll import PayrollRun, SalaryAdvance
from app.models.user import (
    PasswordResetToken,
    RefreshToken,
    User,
    UserRoleAssignment,
)

__all__ = [
    "AdjustmentType",
    "AIFeature",
    "AIUsageLog",
    "Attendance",
    "AttendanceStatus",
    "AuditLog",
    "Branch",
    "BranchNotificationSettings",
    "Child",
    "ChildGuardian",
    "DailyJobRun",
    "DailyReport",
    "DailyReportFile",
    "Enrollment",
    "EnrollmentStatus",
    "Expense",
    "ExpenseCategory",
    "ExpenseStatus",
    "FeePlan",
    "File",
    "FileScanStatus",
    "FoodProduct",
    "FoodStockMovement",
    "Gender",
    "Group",
    "GroupTeacher",
    "GuardianRelationship",
    "Invoice",
    "InvoiceAdjustment",
    "InvoiceStatus",
    "KindergartenSettings",
    "KnowledgeCategory",
    "KnowledgeDocument",
    "MealStatus",
    "MessageDirection",
    "Meal",
    "MealIngredient",
    "MealLog",
    "Mood",
    "Notification",
    "NotificationChannel",
    "NotificationStatus",
    "NotificationType",
    "OutboxEvent",
    "OutboxStatus",
    "ParentMessage",
    "PasswordResetToken",
    "PaymentAllocation",
    "PaymentMethod",
    "PaymentStatus",
    "PaymentTransaction",
    "PayrollRun",
    "SalaryAdvance",
    "PayrollStatus",
    "RefreshToken",
    "Role",
    "StaffPosition",
    "StockMovementReason",
    "StockMovementType",
    "TelegramInvitation",
    "User",
    "UserRoleAssignment",
]
