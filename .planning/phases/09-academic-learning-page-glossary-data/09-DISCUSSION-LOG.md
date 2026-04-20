# Phase 9: Academic/Learning Page & Glossary Data - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-18
**Phase:** 09-academic-learning-page-glossary-data
**Areas discussed:** Content Structure, Glossary Data Model, Search & Filtering, Page Layout & Navigation

---

## Content Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Full page cho mỗi entry | Mỗi khái niệm là 1 trang riêng (/learn/technical/rsi) | |
| Expandable cards | Danh sách cards, click mở rộng để đọc chi tiết | |
| Accordion | Tất cả entries trong 1 trang dài, collapse/expand | |
| Bạn quyết định | Agent's discretion | ✓ |

**User's choice:** Bạn quyết định (Agent's discretion)
**Notes:** Agent recommends expandable cards for scanability + depth balance

| Option | Description | Selected |
|--------|-------------|----------|
| Ngắn gọn | 1-2 đoạn, định nghĩa + công thức + cách dùng cơ bản | |
| Vừa đủ | 3-5 đoạn: định nghĩa, công thức, cách đọc, ví dụ | |
| Chi tiết | Bài viết dài với ví dụ + lưu ý + liên kết khác | ✓ |
| Bạn quyết định | | |

**User's choice:** Chi tiết — bài viết dài với ví dụ + lưu ý + liên kết khác

| Option | Description | Selected |
|--------|-------------|----------|
| Tiếng Việt 100% | Như báo cáo AI hiện tại | |
| Tiếng Việt + thuật ngữ Anh | VD: Chỉ số sức mạnh tương đối (RSI) | ✓ |
| Bạn quyết định | | |

**User's choice:** Tiếng Việt với thuật ngữ tiếng Anh trong ngoặc

---

## Glossary Data Model

| Option | Description | Selected |
|--------|-------------|----------|
| Typed TypeScript module | Một file glossary.ts export data | |
| JSON files theo category | technical.json, fundamental.json, macro.json | |
| MDX files | Mỗi entry là 1 file MDX riêng | |
| Bạn quyết định | | ✓ |

**User's choice:** Bạn quyết định
**Notes:** Agent will use typed TypeScript module per REQUIREMENTS (LEARN-02)

| Option | Description | Selected |
|--------|-------------|----------|
| 15-20 entries | Tối thiểu theo REQUIREMENTS | |
| 25-30 entries | Đủ đầy đủ cho 3 categories | |
| 40+ entries | Bao quát hầu hết chỉ số | |
| Bạn quyết định | | ✓ |

**User's choice:** Bạn quyết định
**Notes:** Agent recommends ~25 entries covering all indicators in the system

---

## Search & Filtering

| Option | Description | Selected |
|--------|-------------|----------|
| Search bar ở đầu trang Learn | Trước categories | |
| Search bar trong mỗi category page | | |
| Sticky search bar | Cố định khi cuộn trang | |
| Bạn quyết định | | ✓ |

**User's choice:** Bạn quyết định
**Notes:** Agent recommends search bar at top of each category page

| Option | Description | Selected |
|--------|-------------|----------|
| Client-side filter | Filter trong mảng data trên client | ✓ |
| Fuse.js fuzzy search | Hỗ trợ tìm gần đúng, typo tolerance | |
| Bạn quyết định | | |

**User's choice:** Client-side filter — simple, fast for ~30 entries

---

## Page Layout & Navigation

| Option | Description | Selected |
|--------|-------------|----------|
| Tab-based | 3 tabs trên 1 trang /learn | |
| Separate pages | 3 routes riêng | |
| Hub + sub-pages | /learn overview + category sub-pages | |
| Bạn quyết định | | ✓ |

**User's choice:** Bạn quyết định
**Notes:** Agent recommends hub + sub-pages per REQUIREMENTS (LEARN-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Có — thêm "Học" vào sidebar | Icon BookOpen | ✓ |
| Không — chỉ qua link từ report | | |
| Bạn quyết định | | |

**User's choice:** Có — thêm item "Học" với icon BookOpen vào sidebar

| Option | Description | Selected |
|--------|-------------|----------|
| Giống style hiện tại | Cards + tables + badge | ✓ |
| Kiểu documentation | Sidebar trái + nội dung phải | |
| Bạn quyết định | | |

**User's choice:** Giống style hiện tại — cards + tables + badge như trang rankings/market

---

## Agent's Discretion

- Card layout and expand/collapse animation
- Number of entries per category
- Entry ordering within categories
- Hub page statistics
- Empty state handling
- URL structure for entries

## Deferred Ideas

- EDU-01: Per-term live example charts (v1.2+)
- EDU-02: Cross-linking between entries (v1.2+)
- EDU-03: AI "giải thích đơn giản hơn" button (v1.2+)
