# Staging API – Upload Path Scalability Backlog

_This backlog tracks the work required to move the image-staging flow from MVP scale (dozens of users, hundreds of images per hour) to full production scale (thousands of users, tens-of-thousands of images per hour)._  
Each item is tagged with a **priority** (P1–P3) and a rough **effort** estimate (📅 = ~days, 🕒 = ~hours).

| # | Task | Priority | Effort | Status |
|---|------|----------|--------|--------|
| 1 | **Async S3 client** – migrate blocking `boto3` calls to `aioboto3` or wrap in `run_in_executor`. | P1 | 📅 2–3 | TODO |
| 2 | **Streamed uploads** – accept `UploadFile` as a stream and pipe directly to S3 (`upload_fileobj` / multipart) to eliminate full file reads into RAM. | P1 | 📅 2 | TODO |
| 3 | **Dynamic concurrency** – replace hard-coded semaphore (5) with ENV/auto-tuned limit and test horizontal scaling with multiple workers. | P1 | 🕒 4 | TODO |
| 4 | **Presigned URL workflow** – generate presigned POST/PUT so clients upload directly to S3; backend stores metadata via S3 events. | P2 | 📅 3–4 | TODO |
| 5 | **Cleanup optimisation** – paginate `list_objects_v2`, batch delete (1000 keys per call), and/or track expiry in DynamoDB; move to scheduled background job. | P2 | 📅 2 | TODO |
| 6 | **Quota caching** – store per-user image counts in Redis & async flush to DB to remove hot-path SQL. | P2 | 🕒 6 | TODO |
| 7 | **Observability** – add structured JSON logging, Prometheus/OpenTelemetry metrics (`uploads_total`, `bytes_uploaded`, `cleanup_duration_seconds`) and alerting. | P2 | 📅 2 | TODO |
| 8 | **Security hardening** – AV scanning, rate limiting, WAF rules, IAM policy review. | P3 | 📅 3 | TODO |
| 9 | **S3 lifecycle rule** – configure bucket to auto-expire `images/` objects after 24 h as a failsafe. | P3 | 🕒 2 | TODO |
| 10 | **Stress & chaos testing** – Locust/k6 load test (500 concurrent), simulate S3 outage to ensure graceful degradation. | P3 | 📅 2 | TODO |

**Owner:** `backend-platform`

_Last updated: 2025-06-19_ 