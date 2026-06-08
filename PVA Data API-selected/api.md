Based on your Excel/API notes and the sample JSON payloads, here’s the clean mapping of:

* API Base URLs
* Endpoints
* HTTP methods
* Request bodies
* Which payload fits which endpoint
* Which property types are supported
* Which external providers are likely involved (CoStar, GreenST, Trepp, ESRI)

---

# 1. Market Data API (CoStar / GreenST)

### Base URL

```txt
http://167.71.28.9
```

### Purpose

* Geocode address
* Fetch market/comparable data
* Uses CoStar + GreenST data sources

### Property Types Likely Supported

* Office
* Retail
* Multifamily (MF)
* Industrial
* Manufactured Housing (possibly through GreenST or MHC collections)

---

## Endpoints

### POST `/api/geocode`

#### Full URL

```txt
http://167.71.28.9/api/geocode
```

#### Best Matching Body

(from your "Market Data" JSON)

```json
{
  "addr":"611 Industrial Way W, Eatontown, NJ 07724",
  "prop_type":"Multifamily",
  "start_period": "2026 Q1",
  "end_period": "2026 Q1"
}
```

#### Notes

Use for:

* Office
* Retail
* MF
* Industrial

Likely returns:

* Coordinates
* Market/submarket
* Nearby comps
* GreenST market metrics
* CoStar market stats

---

### POST `/api/geocode/greenst`

#### Full URL

```txt
http://167.71.28.9/api/geocode/greenst
```

#### Suggested Body

```json
{
  "addr":"611 Industrial Way W, Eatontown, NJ 07724",
  "prop_type":"Industrial"
}
```

#### Notes

Probably GreenST-specific enrichment:

* sustainability
* demographics
* ESG
* market overlays

---

### POST `/api/geocode/hotel`

#### Full URL

```txt
http://167.71.28.9/api/geocode/hotel
```

#### Body

```json
{
  "addr":"Miami Beach, FL"
}
```

Hotel-only endpoint.

---

### POST `/api/geocode/json/hotel`

Likely JSON-formatted hotel response version.

---

# 2. Trepp CSV API

### Base URL

```txt
http://68.183.140.117
```

### Endpoint

```txt
/api/trepp?prop_type=
```

---

## Full URL Example

### Office

```txt
http://68.183.140.117/api/trepp?prop_type=Office
```

### Retail

```txt
http://68.183.140.117/api/trepp?prop_type=Retail
```

### Multifamily

```txt
http://68.183.140.117/api/trepp?prop_type=Multifamily
```

### Industrial

```txt
http://68.183.140.117/api/trepp?prop_type=Industrial
```

### Manufactured Housing

Try:

```txt
http://68.183.140.117/api/trepp?prop_type=Manufactured Housing
```

OR:

```txt
http://68.183.140.117/api/trepp?prop_type=MHC
```

---

## Notes

Likely returns:

* Income & Expense
* Loan metrics
* Cap rates
* Debt coverage
* NOI
* Occupancy
* Historical comps

No POST body needed (query param only).

---

# 3. ESRI Data API

### Base URL

```txt
http://144.126.221.84
```

### Endpoint

```txt
POST /api/esri
```

---

## Full URL

```txt
http://144.126.221.84/api/esri
```

---

## Correct Matching Body

(Your ESRI JSON perfectly matches this endpoint)

```json
{
  "geographies": {
    "State": [
      "01",
      "13",
      "33",
      "49"
    ],
    "CBSA": [
      "11260",
      "48540"
    ],
    "Country": [
      "01"
    ]
  },
  "variables": [
    "TOTPOP00",
    "TOTPOP10",
    "TOTPOP20",
    "TOTPOP_CY",
    "TOTPOP_FY"
  ]
}
```

---

## Returns Likely

* Population
* Growth
* Income
* Demographics
* Household data
* ESRI socioeconomic metrics

---

# 4. Hotel / Manufactured Housing Collections API

### Base URL

```txt
http://164.92.110.143
```

---

# Manufactured Housing Endpoint

## GET `/api/mhp`

### Full URL Example

```txt
http://164.92.110.143/api/mhp?addr=1000 9th Ave, Pensacola, FL 32501&radius=10
```

---

## Notes

THIS is your strongest Manufactured Housing endpoint.

Likely returns:

* Nearby manufactured housing parks
* Mobile home communities
* Comparable parks
* Nearby MHC inventory

---

# Hotel Endpoint

## GET `/api/hotel`

### Full URL Example

```txt
http://164.92.110.143/api/hotel?addr=Miami Beach, FL&radius=10
```

---

# 5. Income & Expense Statements API

### Base URL

```txt
http://138.197.26.81
```

---

# Query Existing Statements

## POST `/PVA_data_model/IE_query`

### Full URL

```txt
http://138.197.26.81/PVA_data_model/IE_query
```

---

## PERFECT Matching Body

(your Income & Expense JSON)

```json
{
  "property_type" : "Office",
  "line_items": true,
  "source":["PVA_Export", "Trepp"],
  "state": ["IL"],
  "latest_stmt": true
}
```

---

## Supported Property Types

You should try:

```json
"property_type":"Office"
```

```json
"property_type":"Retail"
```

```json
"property_type":"Industrial"
```

```json
"property_type":"MF"
```

```json
"property_type":"Manufactured Housing"
```

---

# Upload/Post New Statements

## POST `/PVA_data_model/IE_post`

### Full URL

```txt
http://138.197.26.81/PVA_data_model/IE_post
```

---

## Suggested Body

Likely accepts statement data:

```json
{
  "property_type":"Office",
  "source":"Trepp",
  "state":"IL",
  "noi": 500000,
  "expenses": 200000
}
```

---

# 6. Investor Survey API

### Base URL

```txt
http://137.184.225.172
```

---

# Endpoint

## POST `/api/investor_survey`

### Full URL

```txt
http://137.184.225.172/api/investor_survey
```

---

## PERFECT Matching Body

(your Investor Summary JSON)

```json
{
  "property_type": ["MF Conventional"],
  "startPeriod": "2025 Q2",
  "endPeriod": "2026 Q1",
  "qualifier": ["Average"],
  "data_source": ["SITUSRERC", "PwC"],
  "metric": ["Discount Rate"]
}
```

---

## Likely Returns

* Discount rates
* Cap rates
* Investor sentiment
* Return expectations
* Institutional survey data

---

# 7. Job Status Tracking

### Base URL

```txt
http://104.131.178.9
```

---

## Upload Status

### POST `/upload-job-status`

#### Full URL

```txt
http://104.131.178.9/upload-job-status
```

---

## Query Most Recent Job

### GET `/jobs/most-recent`

#### Full URL

```txt
http://104.131.178.9/jobs/most-recent
```

---

# 8. Top Employers API

### Status

Pending hosting.

### Planned Endpoint

```txt
/top-employers
```

Likely GreenST + scraped PVA data.

---

# BEST PROPERTY TYPE NORMALIZATION

You should standardize property types internally like:

| UI Name              | API Name             |
| -------------------- | -------------------- |
| Office               | Office               |
| Retail               | Retail               |
| Multi Family         | Multifamily          |
| MF                   | Multifamily          |
| Industrial           | Industrial           |
| Manufactured Housing | Manufactured Housing |
| MHC                  | Manufactured Housing |

---

# WHICH API FITS WHICH PROPERTY TYPE

| Property Type        | APIs                                          |
| -------------------- | --------------------------------------------- |
| Office               | Market Data, Trepp, IE Query, Investor Survey |
| Retail               | Market Data, Trepp, IE Query                  |
| Multifamily          | Market Data, Trepp, Investor Survey, IE Query |
| Industrial           | Market Data, Trepp, IE Query                  |
| Manufactured Housing | `/api/mhp`, possibly Trepp + Market Data      |

---

# IMPORTANT MATCHES YOU ALREADY HAVE

| JSON File             | Matching Endpoint          |
| --------------------- | -------------------------- |
| ESRI JSON             | `/api/esri`                |
| Income & Expense JSON | `/PVA_data_model/IE_query` |
| Investor Summary JSON | `/api/investor_survey`     |
| Market Data JSON      | `/api/geocode`             |

---

# MOST IMPORTANT ENDPOINTS FOR YOUR PROJECT

If you're collecting property fields for:

* Office
* Retail
* MF
* Industrial
* Manufactured Housing

These are your primary APIs:

```txt
POST http://167.71.28.9/api/geocode
GET  http://68.183.140.117/api/trepp?prop_type=
POST http://144.126.221.84/api/esri
GET  http://164.92.110.143/api/mhp
POST http://138.197.26.81/PVA_data_model/IE_query
POST http://137.184.225.172/api/investor_survey
```
