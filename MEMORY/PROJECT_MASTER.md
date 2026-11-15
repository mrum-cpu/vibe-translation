# PROJECT_MASTER.md
> ملف الهوية الرئيسي للمشروع. يُحدَّث آلياً بواسطة PROJECT ENGINE.

## BOOK_ID
(يُحدد عند استلام المصدر)

## BOOK_TITLE
(غير محدد — بانتظار المصدر)

## SOURCE_LANGUAGE
(غير محدد)

## TARGET_LANGUAGE
Arabic

## CONSTITUTION
QWEN TRANSLATION SYSTEM — MASTER CONSTITUTION v2.0 (نص الدستور مقدم من المستخدم في بداية المشروع وهو ملزم).

## ROLES
- QWEN: التحليل، الترجمة، المراجعة، اتخاذ القرارات الترجمية العادية.
- PROJECT ENGINE: الحفظ، التحقق، الحالة، الدمج، التقارير (منفذ في ENGINE/).
- USER: السياسة العامة، القرارات الجوهرية، الاستلام النهائي.

## UNIT LIFECYCLE
NOT_STARTED → INGESTED → TRANSLATING → TRANSLATED → QA → QA_PASSED → APPROVED → FINAL
فشل: QA_FAILED → REVISION → QA

## SESSION RESUME ORDER
PROJECT_STATE.json → PROJECT_MASTER.md → GLOSSARY.md → NAME_REGISTER.md → DECISION_LOG.md → LAST_FINAL_UNIT
