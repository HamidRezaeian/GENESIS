# GENESIS — بررسی عمیق و برنامه‌ی اصلاح برای سازنده‌ی پروژه

> تاریخ بررسی: 2026-07-30

> **وضعیت اجرا — به‌روزرسانی 2026-07-31 (Session 15, branch `arena/019fb620-genesis`):**
> ✅ **انجام‌شده:** P0‑1 (تکثیر brain_io + AST guard), P0‑2 (pyproject + قالب CI در `Docs/CI_WORKFLOW.yml.template` — فعال‌سازی Actions نیازمند کپیِ آن به `.github/workflows/` توسط مالک ریپوست، چون توکن اپ اجازه‌ی workflows ندارد),
> P0‑3 (حذف override پنهان RAM؛ engine حاکم بر sizing), P0‑4 (capacity_resolver = لایه‌ی گزارشگر read-only),
> P0‑5 (کف صادقانه‌ی population بدون MIN اجباری), P1‑1/P1‑2 (counterهای natural/refuge/ark/auto_repro births
> + natural deaths + extinctions — که قبلاً تعریف شده ولی هرگز افزایش نمی‌یافتند — سیم‌بندی و در payload منتشر شدند),
> P1‑9 (GENESIS_LIVE_WEB=0 واقعاً جداسازی می‌کند؛ fetch غیرمسدودکننده با thread پس‌زمینه), P1‑10 (ردیابی و حذف
> fake telemetry به‌همراه guard در `tests/telemetry_honesty_test.py`), P1‑11 (یک publisher با seq-gate؛
> RAM با کادانس 1Hz؛ metrics سبک), P2‑3 (بهداشت repo و .gitignore), P2‑4 (تمام لینک‌های dangling اصلاح شدند).
> ✅ **همچنین در همان روز تکمیل شد:** P0‑6 — لوله‌کشی کامل leaderboard واقعی: درایور پیش‌ثبت‌شده‌ی TF1
> (arms × ۳ seed × remap 0/1)، گیت‌های صدور گواهی (G1 sanity ابزار + G2 completeness)، انتشار
> latest.json با hash مانیفست، و رندر داشبورد فقط در صورت certified=true. **اولین سطر واقعی:**
> swap_delta=+1.49pts (توصیفی، n=3). در مسیر، سه ریشه‌ی بزرگ عدم‌تکرارپذیری هم کشف و اصلاح شد
> (seed نشدن random پایتون، RNG داخلی numba که از پایتون قابل seed نیست — seed_kernel_rng اضافه شد،
> و شناور بودن هندسه‌ی poolها با حافظه‌ی آزاد میزبان — pin در درایورها). جزئیات کامل در Result.md Exp 93.
> ✅ **Session 16 (همان روز):** P1‑4 برای TF1 ارتقا یافت — رانِر از n=3 توصیفی به **n=8 با آزمون
> permutation زوجیِ دقیق (sign-flip، دوطرفه، پیش‌ثبت‌شده در کد)** رسید؛ حداقل p قابل‌دستیابی
> در n=8 برابر ۰٫۰۰۷۸. نتیجه‌ی تأییدی (DIV=1): mean delta = **+۴٫۲۶** (۶/۸ مثبت)،
> **p=۰٫۱۵۶** → سیگنال مثبتِ جهت‌دار ولی در آلفای ۰٫۰۵ حل‌نشده. سوییپ حساسیت DIV∈{1,8,32}
> (+ تأیید تجربیِ بی‌اثر بودن DIV روی ablation، بایت‌به‌بایت یکسان) نشان داد جهت مثبت محصول
> DIV=1 نیست و هیچ‌کدام معنادار نمی‌شوند. تکرارپذیری متقابلِ احضان‌ها دوباره بایت‌به‌بایت
> تأیید شد (هم‌پوشانی کامل با سطر n=3). **Exp 94b (n=24، پیش‌ثبت‌شده و الزام‌آور)** به‌عنوان
> داوری نهاییِ تأییدی ثبت شد؛ نتیجه در Result.md Exp 94(c). جزئیات: Result.md Exp 94.
>
> ⚠️ **بازمانده:**
> P1‑4 (تعمیم permutation/bootstrap به خانواده‌های ۲ تا ۵؛ داوری 94b), P1‑3 (کنترل‌های کامل learning), P1‑5 (shortcut audit خودکار),
> P1‑6/P1‑7 (نام‌گذاری دقیق measured-vs-estimated + سند حساسیت exchange rate), P1‑8 (اشتقاق AUTO_REPRO_THRESH),
> P1‑12 (barrier/snapshot ownership برای checkpoint), P2‑1/P2‑2 (شکستن monolith و سازمان‌دهی experiments).
> جزئیات هر فاز در `Docs/RESUME_NEXT_SESSION.md` (Session 15).
>
> این سند برای تحویل به هوش مصنوعی سازنده‌ی GENESIS تهیه شده است. هدف آن ثبت دقیق وضعیت فعلی، ایرادهای فنی و علمی، اولویت اصلاحات، و معیارهای پذیرش پیش از ادامه‌ی توسعه است.

---

## 1. خلاصه‌ی اجرایی

GENESIS یک پروژه‌ی تحقیقاتی بزرگ برای بررسی تکامل، یادگیری درون‌عمر، حافظه، انتخاب طبیعی، اقتصاد محاسباتی و شبکه‌های عصبی اسپایکی روی یک substrate شبیه RAM است.

پروژه از نظر ایده، ambition، ثبت نتایج منفی و تلاش برای falsifiable کردن ادعاها بسیار قوی است. بااین‌حال هنوز نباید آن را AGI اثبات‌شده یا یک شبیه‌ساز کاملاً قابل‌تکرار و از نظر فیزیکی خالص دانست.

مهم‌ترین نتیجه‌ی بررسی:

> قبل از افزودن mechanic، economy یا قابلیت جدید، باید زیرساخت بازتولیدپذیری، تست، متریک capability، حسابداری فیزیکی و جداسازی confoundها اصلاح شود.

### مهم‌ترین blockerهای فعلی

1. فایل `src/brain_io.py` دوبار به‌صورت ناقص/تکراری در همان فایل قرار گرفته است.
2. dependency manifest و مسیر استاندارد اجرای تست‌ها وجود ندارد.
3. `genesis_lab.py` مقدار `GENESIS_RAM_SIZE=1048576` را به‌صورت پیش‌فرض تحمیل می‌کند و hardware-aware sizing engine را عملاً bypass می‌کند.
4. `auto_capacity.py` مقادیر مهم معماری را duplicate و hardcode کرده است.
5. حداقل population می‌تواند در سیستم کم‌حافظه باعث allocation/OOM شود.
6. physical cost model هنوز در بخش‌هایی proxy یا تخمینی است، نه اندازه‌گیری کامل hardware.
7. درآمد `CELL_STATES=256` هنوز exchange-rate کاملاً اندازه‌گیری‌شده نیست.
8. `AUTO_REPRO_THRESH=200000` پارامتر selection-relevant و عمدتاً designer-chosen است.
9. refugium، Ark و founder persistence می‌توانند متریک population و selection را منحرف کنند.
10. live Internet input آزمایش‌ها را غیرقابل‌تکرار می‌کند.
11. `except Exception: pass` خطاهای مهم را پنهان می‌کند.
12. ارسال کل RAM به‌صورت base64 در هر snapshot پرهزینه و با هدف raw-cost ناسازگار است.
13. `genesis_lab.py` و `neuromorphic_engine.py` بیش از حد monolithic شده‌اند.
14. capability و finish line در عمل هنوز به‌اندازه‌ی کافی formal و executable نیستند.

---

## 2. GENESIS در حال حاضر چیست؟

### اجزای اصلی

- substrate یک‌بعدی مبتنی بر آرایه‌ی RAM
- organismهای دارای genome بایتی
- decode ژنوم به neuron، synapse، receptor، sensor و actuator
- LIF و STDP با Numba
- متابولیسم بر اساس هزینه‌ی محاسباتی
- mutation، reproduction، selection و Lamarckian consolidation
- CAM، scratchpad، delay buffer و working-memory mechanism
- اقتصاد غذا، کتاب، خواندن، پیش‌بینی و stigmergy
- peer prediction و Red Queen
- داشبورد WebSocket و HTML/JS
- Brain checkpoint و hall-of-fame
- benchmarkها و notebookهای CUDA برای scaling

### هدف نهایی تعریف‌شده در اسناد

1. خودسازمان‌دهی شبکه‌ی عصبی
2. یادگیری واقعی درون‌عمر
3. انتخاب تکاملی برای کارایی
4. حافظه‌ی بلندمدت و reasoning
5. رفتارهای ارتباطی و compositional
6. capability قابل‌اندازه‌گیری با footprint غیرنزولی
7. رسیدن به یک finish line کمی و قابل ابطال، نه صرفاً survival بیشتر

### برداشت دقیق از وضعیت فعلی

GENESIS فعلاً بیشتر یک **آزمایشگاه برای آزمودن load-bearing بودن یادگیری، حافظه و انتخاب روی substrate محاسباتی** است تا یک AGI ساخته‌شده.

این موضوع منفی نیست؛ اما مرز ادعا باید دقیق و علمی بماند.

---

## 3. نقاط قوتی که باید حفظ شوند

### 3.1. صداقت در ثبت null result و confound

ثبت retract شدن Exp 85 بعد از کشف این‌که births صفر بوده، رفتار علمی بسیار خوبی است. این رویه باید حفظ شود.

نتایج باید همچنان به دسته‌های زیر تقسیم شوند:

- implemented
- scaffold
- goal
- null result
- structural advantage
- survivorship confound
- confirmed result

### 3.2. Rule 18 و Rule 20

این دو اصل از بهترین قسمت‌های پروژه هستند:

- finish line کمی و falsifiable
- الزام به shortcut control، null control و marginal-matched control

هیچ claim شناختی نباید بدون این کنترل‌ها تأیید شود.

### 3.3. flat pools و Numba

استفاده از flat global arrays، preallocation و Numba برای hot path تصمیم مناسبی است و باید حفظ شود.

### 3.4. self-describing checkpoint

ایده‌ی fingerprint برای جلوگیری از decode شدن ژنوم با architecture ناسازگار بسیار مهم است و باید حفظ و تست شود.

### 3.5. Exp 91

Exp 91 از آزمایش‌های قبلی معتبرتر است، چون شامل:

- محیط non-stationary
- remap دوره‌ای
- reproduction
- مقایسه‌ی plastic/fixed-reflex
- چند seed
- گزارش births

است. بااین‌حال هنوز برای ادعای AGI، reasoning یا general intelligence کافی نیست.

---

# 4. ایرادهای فنی و اقدامات اصلاحی

## P0-1 — پاک‌سازی فوری `src/brain_io.py`

### مشاهده

`brain_io.py` شامل دو نسخه‌ی تکراری از header، importها و چند تابع است. تعریف اول `_entries_from_loaded` در میانه‌ی بدنه قطع شده و نسخه‌ی دوم بعداً آن را overwrite می‌کند.

توابعی که duplicate هستند:

- `current_fingerprint`
- `fingerprint_hash`
- `_fp_from_loaded`
- `_entries_from_loaded`

### خطر

- رفتار فعلی به overwrite شدن تعریف اول وابسته است.
- maintenance و code review گمراه‌کننده می‌شود.
- ممکن است فقط یکی از دو نسخه تغییر کند.
- احتمال ایجاد bug در آینده بالا است.

### اقدام لازم

- فایل را به یک نسخه‌ی یکتا و تمیز تبدیل کن.
- هر تابع فقط یک تعریف داشته باشد.
- تست roundtrip، monotonic merge، keep-k و fingerprint mismatch حفظ شود.
- یک تست AST اضافه کن که duplicate top-level function/class را رد کند.

### معیار پذیرش

```text
python -m py_compile src/brain_io.py
python tests/brain_io_test.py
```

باید بدون duplicate definition و بدون خطا اجرا شود.

---

## P0-2 — ایجاد dependency و test workflow رسمی

### مشاهده

در repository، مسیر استاندارد مشخصی برای نصب dependencyها پیدا نشد. `pytest` و حتی `numpy` در محیط بررسی نصب نبودند.

### خطر

- تست‌ها قابل اجرای فوری نیستند.
- نتایج برای شخص ثالث بازتولیدپذیر نیستند.
- نسخه‌ی NumPy، Numba و Python مشخص نیست.

### اقدام لازم

یکی از این ساختارها را اضافه کن، ترجیحاً `pyproject.toml`:

```text
pyproject.toml
requirements.lock یا uv.lock
pytest.ini
.github/workflows/ci.yml
```

حداقل dependencyها:

- Python version constraint
- numpy
- numba
- websockets
- psutil در صورت استفاده
- pytest

### CI حداقلی

CI باید این مراحل را اجرا کند:

1. نصب dependencyها
2. compileall
3. unit tests
4. brain checkpoint tests
5. invariant tests
6. یک smoke test کوتاه و bounded
7. بررسی نبودن duplicate تعریف‌ها

---

## P0-3 — اصلاح RAM sizing و حذف override پنهان

### مشاهده

در `src/genesis_lab.py` مقدار زیر به‌صورت پیش‌فرض set می‌شود:

```python
os.environ.setdefault("GENESIS_RAM_SIZE", "1048576")
```

این کار باعث می‌شود derivation سخت‌افزاری موجود در engine bypass شود.

### مشکل

در اسناد، RAM hardware-aware معرفی شده است، اما entry point اصلی مقدار ثابت 1MB را تحمیل می‌کند.

### اقدام لازم

- default ثابت را از `genesis_lab.py` حذف کن.
- یک resolver مرکزی برای RAM بساز.
- precedence را روشن کن:
  1. override صریح کاربر
  2. cgroup/container limit
  3. available memory
  4. fallback محدود و مستند
- مقدار نهایی واقعی را در startup log و experiment manifest ثبت کن.

### معیار پذیرش

دو اجرای زیر باید رفتار شفاف و قابل مشاهده داشته باشند:

```text
GENESIS_RAM_SIZE=65536 ...
GENESIS_RAM_SIZE=1048576 ...
```

و در حالت بدون override، مقدار واقعی derived ثبت شود.

---

## P0-4 — single source of truth برای capacity

### مشاهده

`auto_capacity.py` مقادیر معماری را مجدداً hardcode کرده است، از جمله:

```python
_N_IO = 39
_NEURONS_PER_ORG = _N_IO + 800
_SYNAPSES_PER_NEURON = 4
_DNA_PER_SYNAPSE = 2.5
```

### خطر

با تغییر engine، memory model و population cap می‌تواند اشتباه شود.

### اقدام لازم

- این مقادیر را از engine یا config metadata مرکزی بخوان.
- هیچ مقدار decode/geometry مهمی نباید در دو فایل مستقل تعریف شود.
- یک `capacity_report()` بساز که موارد زیر را نشان دهد:
  - bytes per neuron
  - bytes per synapse
  - bytes per organism index
  - genome bytes
  - overhead
  - total reserved memory
  - population cap

### معیار پذیرش

تست باید بررسی کند که مقادیر capacity با poolهای واقعی engine سازگارند.

---

## P0-5 — حذف minimum population خطرناک

### مشاهده

`MIN_ORGANISMS = 100` حتی در صورت ناکافی بودن budget می‌تواند ۱۰۰ organism را برگرداند.

### خطر

در machine کوچک یا container محدود، allocation می‌تواند به OOM منجر شود.

### اقدام لازم

- minimum population را به زور اعمال نکن.
- اگر budget کافی نیست، خطای روشن و قابل‌تشخیص بده.
- یا `min_orgs` را explicit و opt-in کن.
- قبل از allocation، memory feasibility check اجرا کن.

---

## P0-6 — تعریف دقیق capability و finish line

### مشکل

Rule 18 معیارهایی مانند افزایش ۲۵٪ capability در ۵M tick را تعریف کرده، اما در کد و experiment protocol هنوز ambiguity وجود دارد.

### مواردی که باید formal شوند

- capability دقیقاً چیست؟
- solve-rate است یا held-out generalization؟
- آیا target در طول عمر تغییر می‌کند؟
- آیا metric روی task جدید اندازه‌گیری می‌شود؟
- monotone trend با چه toleranceای؟
- baseline regression چگونه تعریف می‌شود؟
- footprint شامل چه چیزهایی است؟
- natural birth، refuge birth و Ark birth چگونه جدا می‌شوند؟

### پیشنهاد metric پایه

حداقل این متریک‌ها را تعریف و version کن:

```text
C_task_in_domain
C_task_held_out
C_task_after_remap
C_learning_delta = plastic - matched_ablation
C_per_footprint
natural_births
refuge_births
ark_reseeds
natural_deaths
mean_generation_depth
```

---

# 5. ایرادهای علمی و اعتبارسنجی

## P1-1 — تفکیک کامل natural birth از refuge و Ark

### مشکل

`sim_loop` در شرایط کاهش population، organism جدید از refuge/fossil bank اضافه می‌کند. این برای جلوگیری از extinction مفید است، اما اگر با births طبیعی قاطی شود، population stability گمراه‌کننده خواهد بود.

### اقدام لازم

برای هر run جدا ثبت کن:

```text
natural_births
refuge_births
ark_births
natural_deaths
refuge_energy_refills
extinction_events
```

### معیار پذیرش

هیچ claim انتخاب طبیعی یا multi-generational evolution نباید فقط بر اساس `population` گزارش شود.

---

## P1-2 — جلوگیری از survivorship confound

Exp 85 و Exp 86 نشان دادند که بدون ثبت births، population می‌تواند صرفاً persistence founder را نشان دهد.

### اقدام لازم

پیش از هر benchmark جدید، schema اجباری زیر را تولید کن:

```json
{
  "seed": 42,
  "arm": "proposed",
  "ticks": 10000,
  "initial_population": 300,
  "natural_births": 0,
  "refuge_births": 0,
  "ark_births": 0,
  "natural_deaths": 0,
  "extinctions": 0,
  "mean_age": 0,
  "generation_depth": 0,
  "capability": 0.0,
  "capability_per_footprint": 0.0,
  "energy": 0.0,
  "git_commit": "...",
  "protocol_version": "..."
}
```

---

## P1-3 — آزمون واقعی load-bearing بودن learning

وجود STDP یا تغییر weight به‌تنهایی learning محسوب نمی‌شود.

برای claim یادگیری باید نشان داده شود:

1. محیط یا mapping تغییر می‌کند.
2. organism در طول عمر بهتر می‌شود.
3. improvement روی held-out task یا mapping جدید نیز دیده می‌شود.
4. matched ablation با plasticity خاموش شکست می‌خورد.
5. هزینه‌ی plasticity حساب می‌شود.
6. founder persistence با multi-generational selection قاطی نیست.

### کنترل‌های ضروری

- plasticity ON
- plasticity OFF
- shuffled target
- fixed reflex
- format-matched null
- marginal-matched null
- held-out remap
- no-refuge run
- no-auto-reproduction run در صورت مرتبط بودن

---

## P1-4 — احتیاط در تفسیر Z-score

با پنج seed و metric گسسته یا bounded، Z-score بسیار بزرگ می‌تواند به‌خاطر variance بسیار کم ایجاد شود و الزاماً evidence قوی به معنای عمومی نباشد.

### اقدام لازم

همراه Z-score این موارد را گزارش کن:

- raw values per seed
- effect size
- confidence interval
- permutation/randomization test
- bootstrap interval
- extinction-adjusted analysis
- trajectory plot

از نتیجه‌گیری سنگین فقط با یک Z-score و `n=5` خودداری کن.

---

## P1-5 — formal کردن shortcut audit

برای هر claim شناختی باید مشخص شود آیا پاسخ از این shortcutها آمده یا نه:

- echo
- bigram
- position
- marginal frequency
- authored/oracle logic
- fixed wiring
- immediate reward
- source text repetition

### معیار پذیرش

هر positive result باید حداقل این خروجی را داشته باشد:

```text
capability_proposed
capability_ablation
capability_null
shortcut_gap
held_out_gap
```

---

# 6. physical grounding و economy

## P1-6 — دقیق‌کردن ادعای physical cost

`physical_cost_model.py` پیشرفت مهمی دارد، اما همه‌ی هزینه‌ها هنوز دقیقاً measured hardware cost نیستند.

### محدودیت‌ها

- `DEFAULT_CLOCK_GHZ = 3.0` فرکانس واقعی CPU را نشان نمی‌دهد.
- microbenchmark primitive الزاماً hot path واقعی را بازنمایی نمی‌کند.
- cache، branch، contention و scheduling در calibration کامل مدل نشده‌اند.
- joule با `joules_per_flop` تخمینی است.
- RAPL در محیط فعلی در دسترس نیست.

### اقدام لازم

هزینه‌ها را با نام دقیق‌تر گزارش کن:

```text
measured_wall_time
calibrated_cycle_proxy
measured_cycles_if_available
measured_joules_if_available
estimated_joules
```

اگر RAPL یا power monitor در دسترس نیست، صریحاً مقدار joule را `unavailable` اعلام کن، نه measured.

---

## P1-7 — بررسی exchange rate درآمد

مقدار `CELL_STATES=256` از `2**8` قابل توضیح است، اما هنوز ثابت نشده که یک byte حل‌شده باید دقیقاً ارزش ۲۵۶ execution-cycle داشته باشد.

### خطر

selection advantage ممکن است از exchange-rate طراحی‌شده حاصل شود، نه از physics واقعی.

### اقدام لازم

یکی از این مسیرها را انتخاب کن و مستند کن:

1. درآمد مستقیماً از resource/work آزادشده اندازه‌گیری شود.
2. income به‌عنوان مدل اطلاعاتی معرفی شود، نه energy واقعی.
3. چند exchange model pre-registered اجرا شود.
4. sensitivity analysis کامل گزارش شود.

---

## P1-8 — بررسی `AUTO_REPRO_THRESH`

مقدار پیش‌فرض:

```python
AUTO_REPRO_THRESH = 200000.0
```

از environment خوانده شدن، آن را فیزیکی نمی‌کند.

### اقدام لازم

- threshold را از ظرفیت واقعی substrate مشتق کن، یا
- آن را genome-encoded/evolvable کن، یا
- در تمام armها ثابت و pre-registered نگه دار و sensitivity report ارائه کن.

هیچ threshold انتخابی نباید فقط به‌خاطر گرفتن نتیجه‌ی بهتر تغییر کند.

---

# 7. live input، telemetry و runtime

## P1-9 — جداسازی live Internet mode از benchmark mode

در `_lay_library()` متن Wikipedia می‌تواند کل RAM را tile کند. این برای demo مفید است، اما benchmark علمی را غیرقابل‌تکرار می‌کند.

### اقدام لازم

- `LIVE_DEMO` و `REPRODUCIBLE_BENCHMARK` را جدا کن.
- برای هر input این موارد را ثبت کن:
  - source URL
  - timestamp
  - raw snapshot یا hash
  - encoding
  - length
- خطای live stream باید در telemetry ثبت شود.
- اگر data در دسترس نیست، run باید `degraded` یا `failed` علامت‌گذاری شود.

---

## P1-10 — حذف `except Exception: pass`

موارد گسترده‌ای از `except Exception: pass` در runtime، streamer، library و WebSocket وجود دارد.

### اقدام لازم

- فقط exceptionهای مشخص را catch کن.
- stack trace و context ثبت شود.
- exceptionهای critical، run را failed کنند.
- telemetry شامل وضعیت زیر باشد:

```text
healthy
warning
degraded
failed
```

---

## P1-11 — سبک‌کردن WebSocket state

ارسال کل RAM به‌صورت base64 در هر snapshot هزینه‌ی بالایی دارد:

- copy
- base64 expansion
- JSON overhead
- serialization CPU
- bandwidth

### اقدام لازم

RAM rendering را از metrics state جدا کن:

- state/metrics با نرخ بالا و کوچک
- RAM snapshot با نرخ پایین
- binary WebSocket frame
- dirty-region یا delta encoding
- در headless mode بدون RAM serialization

---

## P1-12 — snapshot و ownership برای state

simulation، websocket، checkpoint و live injection هم‌زمان به global arrays دسترسی دارند.

### خطر

- serialize شدن state نصفه
- checkpoint وسط mutation
- injection وسط tick
- race در telemetry

### اقدام لازم

- mutation فقط بین tickها
- barrier مشخص بین kernel و host
- immutable snapshot برای UI
- checkpoint فقط از snapshot پایدار
- schema version برای state payload

---

# 8. مشکلات معماری و نگهداری

## P2-1 — شکستن فایل‌های monolithic

`neuromorphic_engine.py` و `genesis_lab.py` بیش از حد مسئولیت دارند.

### ساختار پیشنهادی

```text
src/
  engine/
    config.py
    genome.py
    neural_kernel.py
    metabolism.py
    reproduction.py
    memory.py
  runtime/
    lab.py
    websocket.py
    streamer.py
  experiments/
    protocol.py
    metrics.py
    manifests.py
  persistence/
    brain_io.py
```

این کار لازم نیست یک‌باره انجام شود. ابتدا interfaceهای روشن تعریف کن، سپس به‌تدریج فایل‌ها را جدا کن.

## P2-2 — سازمان‌دهی experimentها

در حال حاضر driverها، JSONها، شکل‌ها و scratch fileها در مسیرهای پراکنده‌اند.

### ساختار پیشنهادی

```text
experiments/
  exp91/
    protocol.md
    driver.py
    manifest.json
    results/
    figures/
```

هر experiment باید canonical بودن خود را مشخص کند.

## P2-3 — جداسازی source و generated artifact

فایل‌های `.vs/`، graph output، checkpointهای بزرگ و بسیاری از figureها نباید بدون policy مشخص در Git بمانند.

### اقدام لازم

- افزودن `.vs/` به `.gitignore`
- انتقال checkpointهای بزرگ به Git LFS یا artifact storage
- جداسازی `generated/` از source
- نگهداری manifest و hash برای artifactهای لازم

## P2-4 — اصلاح مسیرهای dangling در docs

References به فایل‌هایی مانند موارد زیر وجود دارد که در مسیرهای فعلی یافت نشدند:

- `Docs/Ascent.md`
- `Docs/Architecture/Ascent.md`
- `Docs/Architecture/FixedRules.md`
- `Docs/Architecture/MagicNumbers.md`

### اقدام لازم

- فایل‌ها را restore کن، یا
- referenceها را به مسیر واقعی اصلاح کن، یا
- لینک‌های قدیمی را حذف کن.

همچنین pathهای سیستم ویندوزی در اسناد agent باید portable شوند.

---

# 9. برنامه‌ی اجرایی پیشنهادی

## فاز ۱ — تثبیت و سلامت repository

1. پاک‌سازی `brain_io.py`
2. ساخت `pyproject.toml`
3. نصب و اجرای pytest
4. ساخت CI
5. حذف `.vs` و artifactهای غیرضروری از Git
6. رفع dangling docs
7. اضافه‌کردن AST duplicate-definition test

## فاز ۲ — تثبیت substrate و ظرفیت

1. حذف RAM default پنهان از `genesis_lab.py`
2. ایجاد capacity resolver مرکزی
3. حذف duplicate constants در `auto_capacity.py`
4. feasibility check قبل از allocation
5. ثبت RAM و pool footprint واقعی
6. تست low-memory و cgroup

## فاز ۳ — تثبیت آزمایش علمی

1. تعریف capability protocol
2. ثبت manifest کامل
3. جداسازی natural/refuge/Ark birth
4. no-refuge control
5. plastic ON/OFF matched control
6. held-out task و remap
7. permutation/bootstrap analysis

## فاز ۴ — اعتبارسنجی economy

1. audit exchange rate
2. audit auto-reproduction threshold
3. audit metabolic cost proxy
4. RAPL یا power measurement روی bare metal
5. جداکردن estimated و measured energy

## فاز ۵ — بهبود runtime

1. snapshot-based telemetry
2. binary/delta RAM streaming
3. حذف broad exception swallowing
4. live mode جدا از benchmark mode
5. checkpoint barrier

## فاز ۶ — refactor تدریجی

1. جداکردن config
2. جداکردن genome decoder
3. جداکردن persistence
4. جداکردن experiment protocol
5. جداکردن UI transport

---

# 10. معیار پذیرش نهایی پیش از claim بزرگ‌تر

پروژه نباید claim جدیدی مانند «AGI»، «reasoning واقعی» یا «emergent language» را معتبر اعلام کند، مگر این‌که همه‌ی موارد زیر موجود باشند:

- [ ] تست‌ها در محیط clean اجرا می‌شوند.
- [ ] نسخه‌ی Python/NumPy/Numba ثبت شده است.
- [ ] commit و manifest آزمایش ثبت شده است.
- [ ] input و hash آن ثبت شده است.
- [ ] plastic ON/OFF matched control اجرا شده است.
- [ ] natural births از refuge/Ark جدا شده‌اند.
- [ ] founder persistence confound رد شده است.
- [ ] capability روی held-out task سنجیده شده است.
- [ ] shortcut control اجرا شده است.
- [ ] exchange rate و reproduction threshold sensitivity گزارش شده‌اند.
- [ ] measured و estimated energy جدا گزارش شده‌اند.
- [ ] نتیجه با raw per-seed data قابل بررسی است.
- [ ] UI فقط telemetry واقعی را نمایش می‌دهد.
- [ ] failureهای runtime پنهان نمی‌شوند.

---

# 11. نتیجه‌ی نهایی بررسی

GENESIS از نظر ایده و جدیت تحقیقاتی پروژه‌ی ارزشمندی است. نقاط قوت اصلی آن عبارت‌اند از:

- دامنه‌ی معماری بلندپروازانه
- استفاده‌ی مناسب از Numba و flat arrays
- ثبت صادقانه‌ی null resultها
- تلاش برای تعریف قوانین فیزیکی و finish line
- وجود benchmarkهای چندمرحله‌ای
- طراحی checkpoint خودتوصیف‌گر

اما قبل از ادامه‌ی توسعه‌ی قابلیت‌های جدید، باید روی سلامت پایه تمرکز شود. مهم‌ترین اولویت‌ها عبارت‌اند از:

1. پاک‌سازی کد و تست‌پذیری
2. reproducibility
3. اصلاح sizing و capacity
4. تعریف capability مستقل
5. جداسازی confoundها
6. شفاف‌سازی physical cost و income
7. تفکیک benchmark از live demo

برداشت نهایی:

> GENESIS هنوز AGI اثبات‌شده نیست؛ اما می‌تواند به یک آزمایشگاه علمی معتبر برای آزمودن یادگیری، حافظه و انتخاب تکاملی تبدیل شود، به شرط آن‌که قبل از افزودن mechanics جدید، زیرساخت آزمایش و اعتبارسنجی آن تثبیت شود.

---

# 12. روش بررسی و محدودیت آن

این بررسی توسط یک Agent در Arena.ai انجام شده و شامل موارد زیر بوده است:

- بررسی ساختار repository و Git status
- مطالعه‌ی PRD، ARD، Roadmap، Result، Runbook و قوانین پروژه
- بررسی استاتیک فایل‌های Python و frontend
- بررسی dependencyها و test entry pointها
- اجرای compile check
- تلاش برای اجرای `tests/brain_io_test.py`
- تحلیل AST برای کشف duplicate definition
- بررسی consistency بین documentation و code
- بررسی سخت‌گیرانه‌ی physics/accounting، experiment validity، reproducibility و architecture

در محیط بررسی، `numpy` و `pytest` نصب نبودند؛ بنابراین اجرای کامل تست‌های runtime ممکن نشد. این محدودیت باید با ایجاد dependency manifest و CI برطرف شود.

همچنین به Fable 5 دسترسی مستقیم وجود نداشت؛ بنابراین نباید ادعا شود که این بررسی توسط Fable 5 انجام شده است.
