# myITS Classroom MCP Server

MCP (Model Context Protocol) server untuk mengakses **myITS Classroom** (`classroom.its.ac.id`) milik Institut Teknologi Sepuluh Nopember. Server ini memungkinkan LLM/agent (Claude, opencode, dsb.) membaca mata kuliah, materi, tugas, deadline, nilai, hingga mengunduh file langsung dari classroom.

---

## 1. Tujuan Teknikal

myITS Classroom **tidak menyediakan API publik berdokumentasi**. Project ini melakukan *reverse engineering* terhadap web client resminya dan membungkusnya menjadi tools standar MCP sehingga bisa dipakai agent AI. Tujuan teknikalnya:

1. **Autentikasi tanpa kredensial** — memanfaatkan session cookie `MoodleSession` dari browser, bukan username/password, agar aman dan tidak menyimpan kredensial.
2. **Akses data terstruktur JSON** — memanggil endpoint AJAX internal Moodle yang sama seperti yang dipakai UI web (dashboard, kalender).
3. **Fallback parsing HTML** — untuk data yang tidak tersedia lewat AJAX (isi course, detail tugas, nilai), server mem-parsing HTML halaman yang sama persis dengan yang dirender browser.
4. **Download file terotentikasi** — file materi (`pluginfile.php`) butuh cookie sesi; server menyalurkannya sebagai tool `download_file`.
5. **Bersih dari dependensi tidak resmi** — semua request identik dengan trafik browser biasa (GET/POST + cookie), tanpa eksploitasi atau bypass apa pun.

---

## 2. Bagaimana MCP Ini Dibuat dari Web Classroom ITS (Reverse Engineering)

### 2.1 Identifikasi Platform

Fetch awal ke `https://classroom.its.ac.id/my/courses.php` membocorkan dua hal penting di dalam variabel `M.cfg` pada HTML:

```js
var M = { "wwwroot": "https://classroom.its.ac.id",
          "apibase":  "https://classroom.its.ac.id/r.php/api",  // API kustom aplikasi mobile
          "sesskey":  "...",                                     // token CSRF internal
          ... };
```

Kesimpulan:
- myITS Classroom adalah **Moodle** (tema RemUI/Open LMS) — semua pola URL mengikuti Moodle: `/course/view.php`, `/mod/assign/view.php`, `/lib/ajax/service.php`, dst.
- Ada `apibase` kustom (`/r.php/api`) yang dipakai aplikasi mobile myITS — tidak berdokumentasi publik dan tidak dipakai project ini.
- `sesskey` adalah token internal yang wajib dikirim untuk setiap call AJAX.

### 2.2 Penyelidikan Jalur Resmi: Moodle Web Service (GAGAL)

Percobaan pertama menggunakan jalur baku Moodle Mobile Web Service:

| Endpoint | Status | Hasil |
|---|---|---|
| `POST /login/token.php` (username+password+service) | hidup | Butuh password lokal Moodle; login ITS umumnya via SSO OIDC |
| `POST /webservice/rest/server.php?wstoken=...` | hidup | Token tidak bisa diperoleh; admin menonaktifkan sebagian besar fungsi |

Kesimpulan: jalur token resmi dinonaktifkan admin → perlu jalur lain.

### 2.3 Jalur yang Berhasil #1: AJAX Internal (`/lib/ajax/service.php`)

UI dashboard Moodle memanggil fungsi internal melalui:

```
POST https://classroom.its.ac.id/lib/ajax/service.php?sesskey=<SESSKEY>&info=<nama>
Content-Type: application/json
Cookie: MoodleSession=<COOKIE>

[{"index":0,"methodname":"<fungsi>","args":{...}}]
```

Cara mendapatkan input-nya (keduanya di-scrape dari satu GET `/my/`):
- `sesskey` → regex `"sesskey":"([^"]+)"`
- `userId` → regex `"userId":(\d+)`

Hasil uji whitelist (fungsi yang diizinkan vs ditolak):

| methodname | Status | Dipakai untuk |
|---|---|---|
| `core_course_get_enrolled_courses_by_timeline_classification` | ✅ | daftar mata kuliah |
| `core_calendar_get_calendar_upcoming_view` | ✅ | deadline per course |
| `core_calendar_get_action_events_by_courses` | ✅ | deadline semua course |
| `core_enrol_get_users_courses` | ❌ servicenotavailable | — |
| `core_course_get_contents` | ❌ servicenotavailable | → scraping |
| `mod_assign_get_assignments` | ❌ servicenotavailable | → scraping |
| `mod_quiz_get_quizzes_by_courses` | ❌ servicenotavailable | → scraping |

Respons sukses berbentuk `[{"error":false,"data":{...}}]`.

### 2.4 Jalur yang Berhasil #2: Scraping HTML Halaman Course

Halaman `/course/view.php?id=<courseid>` merender seluruh konten server-side dengan struktur yang stabil:

```html
<li class="section ...">
  <h3 class="sectionname">TM-11 8 Mei 2026</h3>
  <li class="activity resource modtype_resource hasinfo">
    <span class="instancename">PPT Estimasi Parameter <span class="accesshide">File</span></span>
    <a href="/mod/resource/view.php?id=310445">...</a>
    <div class="activity-dates">Opened: ... Due: ...</div>
```

Parser (`_parse_course_page`) mengekstrak per aktivitas:
- `cmid` — course module id dari query `?id=` pada link
- `modtype` — dari class `modtype_*` (assign, resource, quiz, zoom, forum, url, page, ...)
- `name` — teks `.instancename` (elemen `.accesshide` dibuang)
- `dates` — isi `.activity-dates` (tanggal open/due jika ada)

Halaman detail tugas (`/mod/assign/view.php?id=<cmid>`) diekstrak dengan kombinasi selector + regex tanggal (`Due date`, `Submitted`, dsb.).

### 2.5 Download File

Resource view (`/mod/resource/view.php?id=<cmid>`) me-redirect 303 ke `pluginfile.php/...`. URL tersebut hanya valid bila disertai cookie `MoodleSession`. Tool `download_file` melakukan GET dengan cookie, lalu menyimpan file (nama asli diambil dari header `Content-Disposition`).

### 2.6 Ringkasan Alur

```
┌─────────────┐  MoodleSession   ┌──────────────────────────────────┐
│ MCP Client  │ ───────────────► │ server.py                        │
│ (Claude/    │                  │                                  │
│  opencode)  │                  │ 1. GET /my/ → sesskey + userId   │
└─────────────┘                  │ 2. Data terstruktur:             │
                                 │    POST /lib/ajax/service.php    │
                                 │    (courses, calendar/deadline)  │
                                 │ 3. Fallback:                     │
                                 │    GET /course/view.php,         │
                                 │    /mod/assign/view.php,         │
                                 │    /grade/report/user/...        │
                                 │    → parse HTML (bs4)            │
                                 │ 4. File: pluginfile.php          │
                                 └──────────────────────────────────┘
```

---

## 3. Referensi Tools

| Tool | Parameter | Keterangan |
|---|---|---|
| `get_profile()` | – | userid akun yang sedang login |
| `list_courses()` | `status`: `inprogress`\|`future`\|`past`\|`all` | daftar mata kuliah (id, nama, progres, tanggal) |
| `get_course_contents()` | `course_id` | semua section + aktivitas (cmid, modtype, nama, url, dates) |
| `get_materials()` | `course_id` | filter materi: resource/url/folder/book/page |
| `get_assignments()` | `course_id` | filter aktivitas bertipe assign |
| `get_assignment_detail()` | `cmid` | judul, due date, status pengumpulan, nilai, deskripsi, lampiran |
| `get_deadlines()` | `course_id?`, `days_ahead` (default 30) | agenda/deadline; tanpa course_id = semua MK, terurut waktu |
| `get_grades()` | `course_id` | tabel nilai (teks hasil scraping laporan nilai) |
| `download_file()` | `url`, `dest_dir` | unduh file pluginfile ke folder lokal |
| `set_session()` | `moodle_session` | set cookie sesi dari chat: validasi → aktif → simpan `.env` |
| `session_status()` | – | cek validitas sesi saat ini |

Contoh respons `get_course_contents(8518)`:

```json
[
  {"section": "Materi", "activities": [
    {"cmid": 167937, "modtype": "resource",
     "name": "Pengenalan Jaringan Komputer",
     "url": "https://classroom.its.ac.id/mod/resource/view.php?id=167937",
     "dates": []}
  ]}
]
```

---

## 4. Keterbatasan

1. **Session expired** — `MoodleSession` mati setelah idle ±8 jam (config `sessiontimeout`). Gejala: error *"Session invalid/expired"*. Solusi: login ulang di browser, copy cookie baru ke `.env`.
2. **Whitelist AJAX terbatas** — hanya fungsi tertentu yang diizinkan; sisanya wajib scraping HTML.
3. **Konten disembunyikan dosen** — section kosong pada beberapa course (mis. Struktur Data 8549) karena availability/restrict di sisi server, bukan bug parser.
4. **Read-mostly** — tidak ada tool submit tugas/absen (sengaja, untuk keamanan akun). Bisa ditambahkan nanti via form POST dengan sesskey.
5. **Scraping rapuh terhadap perubahan tema** — jika ITS mengganti struktur HTML RemUI, selector di `_parse_course_page` perlu disesuaikan.

---

## 5. Cara Pakai

### 5.1 Instalasi

Menggunakan `uv` (direkomendasikan):

```bash
cd ~/myits-classroom-mcp
uv venv
uv pip install -r requirements.txt
```

Atau pip standar:

```bash
cd ~/myits-classroom-mcp
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

---

### 5.2 Mengisi Sesi: Lewat Chat atau .env

Ada dua cara memberikan cookie `MoodleSession`:

**Cara A — lewat chat (direkomendasikan, tanpa edit file):**

1. Login ke [classroom.its.ac.id](https://classroom.its.ac.id) di browser.
2. DevTools (F12) → **Application** → **Cookies** → copy nilai `MoodleSession`.
3. Tempel ke agent, misalnya:
   > *"ini session classroom-ku: `abc123def456...`, set dong"*
4. Agent akan memanggil tool `set_session(moodle_session=...)` yang:
   - memvalidasi cookie langsung ke server (kalau invalid/expired → ditolak dengan pesan jelas),
   - mengaktifkannya untuk semua tool berikutnya dalam proses yang sama,
   - **menyimpannya permanen** ke `.env` (atomic write via temp file + rename), sehingga tetap terpakai setelah MCP direstart.

Tool pendukung:

| Tool | Fungsi |
|---|---|
| `set_session(moodle_session)` | validasi + aktifkan + simpan ke `.env` |
| `session_status()` | cek sesi valid/tidak dan userid pemiliknya |

Alur khas agent saat sesi mati:

```
user : "deadline minggu ini apa?"
agent: panggil get_deadlines() -> error "MOODLE_SESSION belum ada / expired"
agent: "Sesi classroom kamu habis. Tolong kirim nilai MoodleSession
        dari browser (F12 > Application > Cookies)."
user : "5e4183..."
agent: panggil set_session(...) -> ok
agent: panggil ulang get_deadlines() -> hasil
```

**Cara B — manual edit `.env`:**

```env
MOODLE_SESSION=nilai_cookie_disini
```

Urutan pembacaan cookie oleh server: `_SESSION_OVERRIDE` (hasil `set_session`) → env var → `.env`.

### 5.3 Daftarkan ke Client MCP

**opencode** (~/.config/opencode/opencode.json):

```json
{
  "mcp": {
    "myits-classroom": {
      "type": "local",
      "command": ["/home/fahmialfayadh/myits-classroom-mcp/.venv/bin/python",
                  "/home/fahmialfayadh/myits-classroom-mcp/server.py"]
    }
  }
}
```

**Claude Desktop** (claude_desktop_config.json):

```json
{
  "mcpServers": {
    "myits-classroom": {
      "command": "/home/fahmialfayadh/myits-classroom-mcp/.venv/bin/python",
      "args": ["/home/fahmialfayadh/myits-classroom-mcp/server.py"]
    }
  }
}
```

### 5.4 Menjalankan Manual / Debug

```bash
cd ~/myits-classroom-mcp
uv run python server.py        # stdio mode (untuk client MCP)
```

Uji cepat tanpa client MCP:

```bash
uv run python -c "
import server
print(server.get_profile())
for c in server.list_courses(): print(c['id'], c['fullname'])
"
```

Uji unit test suite:

```bash
uv run python -m unittest discover -s tests
```

### 5.5 Contoh Prompt untuk Agent

Setelah MCP aktif, cukup bicara natural:

- *"Ajar mata kuliah gue dong"* → `list_courses`
- *"Deadline minggu ini apa aja?"* → `get_deadlines(days_ahead=7)`
- *"Ambil materi Jaringan Komputer"* → `list_courses` → `get_course_contents`
- *"Tugas Routing Protokol due-nya kapan? udah kekumpul belum?"* → `get_assignment_detail(cmid=314710)`
- *"Download PPT Layer Aplikasi"* → `download_file(url=...)`

---

## 6. Struktur Project (N-Tier Architecture)

Project ini menerapkan **N-Tier Architecture** dengan pemisahan layer yang jelas:

```
myits-classroom-mcp/
├── server.py                            # Entry point utama (FastMCP server & backward compatibility)
├── requirements.txt                     # Dependensi: fastmcp, httpx, beautifulsoup4, python-dotenv
├── .env                                 # MOODLE_SESSION (jangan di-commit!)
├── README.md                            # Dokumen teknis
├── tests/                               # Test suite
│   └── test_architecture.py             # Unit test pemisahan layer & registrasi tool
└── src/                                 # Package Utama
    ├── config.py                        # Konfigurasi sistem, URL dasar, & regex
    ├── domain/                          # Domain Tier (DTO & Type Definitions)
    │   └── models.py                    # Data classes & TypedDict (CourseInfo, AssignmentDetail, dll)
    ├── infrastructure/                  # Infrastructure / Data Access Tier
    │   ├── session_repository.py        # Sesi & penyimpan .env
    │   ├── moodle_client.py             # Wrapper HTTP Client (httpx)
    │   ├── moodle_ajax.py               # Komunikasi AJAX Moodle (/lib/ajax/service.php)
    │   ├── moodle_parser.py             # HTML Scraper & Parser (BeautifulSoup)
    │   └── file_downloader.py           # Downloader file terotentikasi
    ├── services/                        # Application / Business Logic Tier
    │   ├── session_service.py           # Layanan manajemen & validasi sesi
    │   ├── user_service.py              # Layanan info profil pengguna
    │   ├── course_service.py            # Layanan mata kuliah, materi, & tugas
    │   ├── assignment_service.py        # Layanan detail tugas & download file
    │   ├── calendar_service.py          # Layanan deadline & agenda kalender
    │   └── grade_service.py             # Layanan laporan nilai
    └── presentation/                    # Presentation Tier
        └── mcp_tools.py                 # Registrasi tools FastMCP (@mcp.tool())
```

