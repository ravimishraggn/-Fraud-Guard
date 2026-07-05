// All user-facing text lives here — no hardcoded strings in components.
export const APP_NAME = "FraudGuard";

export const TEXT = {
  login: {
    title: "Sign in to FraudGuard",
    emailLabel: "Email address",
    passwordLabel: "Password",
    submit: "Sign in",
    registerPrompt: "New to FraudGuard?",
    registerLink: "Create an account",
    error: "Incorrect email or password.",
  },
  register: {
    title: "Create your FraudGuard account",
    companyLabel: "Company name",
    nameLabel: "Your full name",
    emailLabel: "Work email",
    passwordLabel: "Password (min 8 characters)",
    submit: "Create account",
    loginPrompt: "Already have an account?",
    loginLink: "Sign in",
    error: "Could not create the account. Please check the details and try again.",
  },
  dashboard: {
    title: "Dashboard",
    docsThisMonth: "Documents this month",
    flagsRaised: "Fraud flags raised",
    moneySaved: "Money saved",
    automationRate: "Automation rate",
    volumeChart: "Daily document volume (last 30 days)",
    recentFlags: "Recent fraud flags",
    pendingAlert: (n: number) => `${n} document${n === 1 ? "" : "s"} waiting for review`,
    reviewNow: "Review now",
    noFlags: "No fraud flags yet. Upload invoices to get started.",
  },
  upload: {
    title: "Upload invoice",
    dropHint: "Drag and drop an invoice here, or click to browse",
    fileTypes: "PDF, JPG or PNG — up to 50 MB",
    whatsappHint: "Or forward invoice photo to WhatsApp: +91 XXXXXXXXXX",
    processing: "Processing your invoice…",
    processingHint: "Extracting fields and running fraud checks. This usually takes under a minute.",
    failed: "We could not process this file.",
    uploadError: "Upload failed. Please try again.",
  },
  review: {
    title: "Review queue",
    empty: "Nothing to review. All caught up!",
    columns: {
      vendor: "Vendor",
      amount: "Amount",
      date: "Date",
      risk: "Risk",
      flags: "Flags",
      uploadedBy: "Uploaded",
      waiting: "Waiting",
    },
  },
  detail: {
    extractedFields: "Extracted fields",
    fraudFlags: "Fraud flags",
    noFlags: "No fraud flags on this document.",
    approve: "Approve",
    reject: "Reject",
    escalate: "Escalate",
    notePlaceholder: "Add a review note (optional)",
    viewMatching: "View matching invoice",
    previewUnavailable: "Preview unavailable for this file.",
  },
  vendors: {
    title: "Vendors",
    empty: "No vendors yet. They appear automatically as invoices are processed.",
    whitelisted: "Whitelisted",
    notWhitelisted: "Not whitelisted",
  },
  rules: {
    title: "Fraud rules",
    defaultSection: "Built-in checks",
    customSection: "Custom rules",
    addCustom: "Add custom rule",
    builtinNote: "Built-in checks can be disabled but not deleted.",
    form: {
      name: "Rule name",
      type: "Rule type",
      maxAmount: "Maximum amount (₹)",
      maxPerMonth: "Max invoices per vendor per month",
      save: "Save rule",
      cancel: "Cancel",
    },
  },
  settings: {
    title: "Settings",
    team: "Team",
    notifications: "Notifications",
    limits: "Plan & limits",
    comingSoon: "Team management, notification preferences and plan limits are managed here.",
  },
  common: {
    loading: "Loading…",
    error: "Something went wrong. Please try again.",
    logout: "Sign out",
    retry: "Retry",
  },
  nav: {
    dashboard: "Dashboard",
    upload: "Upload",
    review: "Review queue",
    vendors: "Vendors",
    rules: "Rules",
    settings: "Settings",
  },
};

export const RISK_COLORS: Record<string, string> = {
  clean: "bg-green-100 text-clean",
  low: "bg-yellow-100 text-yellow-700",
  medium: "bg-orange-100 text-medium",
  high: "bg-red-100 text-danger",
  unknown: "bg-gray-100 text-gray-500",
};

export const SEVERITY_COLORS: Record<string, string> = {
  low: "border-gray-300 bg-gray-50",
  medium: "border-orange-300 bg-orange-50",
  high: "border-red-300 bg-red-50",
  critical: "border-red-500 bg-red-50",
};

export const SEVERITY_ICONS: Record<string, string> = {
  low: "🟡",
  medium: "🟠",
  high: "🔴",
  critical: "🔴",
};
