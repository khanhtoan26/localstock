# Phase 11: Admin API Endpoints - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-21
**Phase:** 11-admin-api-endpoints
**Areas discussed:** API Structure, Job Tracking, Stock Watchlist, Granular Operations

---

## API Structure

| Option | Description | Selected |
|--------|-------------|----------|
| /api/admin/* router mới | Tách biệt admin với public API, dễ thêm auth sau | ✓ |
| Mở rộng /api/automation/* | Ít file hơn nhưng mix admin + public | |

**User's choice:** /api/admin/* router mới — tách biệt admin với public API
**Notes:** None

---

## Job Tracking

| Option | Description | Selected |
|--------|-------------|----------|
| DB persistence (PostgreSQL) | Lưu vào PostgreSQL, query lịch sử dễ dàng | ✓ |
| In-memory | Đơn giản, mất khi restart | |

**User's choice:** DB persistence — lưu vào PostgreSQL, query lịch sử dễ dàng
**Notes:** None

---

## Stock Watchlist

| Option | Description | Selected |
|--------|-------------|----------|
| Thêm cột is_tracked vào bảng stocks | Không tạo bảng mới, đơn giản | ✓ |
| Bảng watchlist riêng (many-to-many) | Linh hoạt hơn cho multi-user | |

**User's choice:** Dùng bảng stocks hiện có + thêm cột is_tracked — không tạo bảng mới, đơn giản
**Notes:** None

---

## Granular Operations

| Option | Description | Selected |
|--------|-------------|----------|
| Granular — crawl, analyze, score, report riêng | Linh hoạt, dễ debug | ✓ |
| Chỉ full pipeline + single-symbol | Đơn giản như hiện tại | |

**User's choice:** Granular — crawl, analyze, score, report riêng — linh hoạt, dễ debug
**Notes:** None

---

## Agent's Discretion

- Pydantic request/response model schemas
- Error handling patterns (follow existing convention)
- Job status enum values

## Deferred Ideas

None
