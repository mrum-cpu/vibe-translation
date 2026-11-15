# PROJECT ENGINE — دليل التشغيل

نظام إدارة مشروع الترجمة (وفق الدستور v2.0). يعمل محلياً ولا يعتمد على ذاكرة النموذج.

## المكونات
| الملف | الوظيفة | البند في الدستور |
|---|---|---|
| `ingest_source.py` | تقسيم المصدر (PDF/TXT) إلى وحدات مرقمة + manifest | §19، §42-B |
| `ingest_package.py` | التحقق من الحزمة وقبولها أو رفضها + تحديث الذاكرة والحالة | §15، §16، §18 |
| `unit_state.py` | انتقالات حالة الوحدة (دورة الحياة الصارمة) | §6 |
| `completeness.py` | تقرير الاكتمال + الاختبارات العشرة النهائية | §20، §35، §36 |
| `build_book.py` | تجميع الكتاب النهائي (لا يجمع إلا بعد نجاح كل الشروط) | §37 |
| `engine_core.py` | الحالة، النسخ الاحتياطي، تحديث سجلات الذاكرة | §33 |

## سير العمل
```bash
# 1) استلام المصدر (مرحلة INGESTING)
python3 ENGINE/ingest_source.py SOURCE/source_original.pdf --book-id BOOK

# 2) بناء BOOK_MAP.md في مرحلة MAPPING (قبل أي ترجمة)

# 3) استقبال حزمة من QWEN (مرحلة TRANSLATING)
python3 ENGINE/ingest_package.py PACKAGES/inbox/<package>.txt

# 4) انتقالات الحالة
python3 ENGINE/unit_state.py U0001 QA_PASSED
python3 ENGINE/unit_state.py U0001 APPROVED
python3 ENGINE/unit_state.py U0001 FINAL

# 5) التقارير
python3 ENGINE/completeness.py

# 6) التجميع (يُرفض إلا بعد اكتمال الشروط)
python3 ENGINE/build_book.py
```

## عقد الحزمة (§15)
العلامات ثابتة: `PACKAGE_START`, `PACKAGE_ID:`, `BOOK_ID:`, `CHAPTER_ID:`,
`UNIT_START:`, `UNIT_END:`, `SOURCE_RANGE:`, `SOURCE_WORD_COUNT:`,
`TRANSLATION_STATUS:`, `TRANSLATION_START/END`, `GLOSSARY_START/END`,
`NAME_REGISTER_START/END`, `DECISIONS_START/END`, `QA_START/END`, `PACKAGE_END`.
الأقسام GLOSSARY / NAME_REGISTER / DECISIONS / QA تستقبل صفوف جداول Markdown
تُلحق آلياً بالملفات المقابلة في MEMORY/.

## الرفض (§18)
حزمة فاشلة تُنقل إلى `PACKAGES/rejected/` مع رسالة `PACKAGE_REJECTED: <سبب>`
ولا تدخل الكتاب النهائي أبداً.

## النسخ الاحتياطي (§33)
كل تعديل على الحالة أو سجلات الذاكرة يحفظ نسخة زمنية في `BACKUPS/` قبل الكتابة.
