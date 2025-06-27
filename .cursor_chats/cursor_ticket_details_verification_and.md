# Ticket details verification and comparison
_Exported on 6/27/2025 at 19:10:01 GMT+5:30 from Cursor (1.1.6)_

---

**User**

does this output match - {Here are the full details from the newly uploaded ticket (`PRY NDLS 20 June.pdf`):

---

### 🎫 **Train Ticket Overview**

* **PNR**: `2717575060`
* **Transaction ID**: `100005853490299`
* **Booking Date**: `13-Jun-2025, 20:59:37 HRS`
* **From**: Prayagraj Junction (PRYJ)
* **To**: New Delhi (NDLS)
* **Journey Date**: **20-Jun-2025**
* **Departure Time**: 22:30 (20-Jun-2025)
* **Arrival Time**: 06:15 (21-Jun-2025)
* **Train**: 12275 / NDLS HUMSAFAR
* **Class**: Third AC (3A)
* **Distance**: 636 KM
* **Quota**: General (GN)

---

### 👥 **Passengers**

| No. | Name             | Age | Gender | Booking Status   | Current Status   |
| --- | ---------------- | --- | ------ | ---------------- | ---------------- |
| 1   | SUCHITRA GUPTA   | 66  | F      | CNF/B10/9/LOWER  | CNF/B10/9/LOWER  |
| 2   | RITA BHATACHARYA | 63  | F      | CNF/B10/12/LOWER | CNF/B10/12/LOWER |

---

### 💰 **Payment Details**

* **Ticket Fare**: ₹2,310.00
* **IRCTC Convenience Fee (incl. GST)**: ₹23.60
* **Travel Insurance Premium**: ₹0.90
* **Total Fare**: ₹2,334.50
* *(Payment Gateway Charges may be extra)*

---

### 🧾 **Tax & Invoice**

* **Invoice Number**: PS25271757506011
* **SAC Code**: 996421
* **Supplier GSTIN**: 07AAAGM0289C1ZL
* **Taxable Value**: ₹2,200
* **IGST (5%)**: ₹110.00
* **Total Tax**: ₹110.00
* **Place of Supply**: Uttar Pradesh (9)
* **Supplier Location**: Delhi/DL

---

### ⚠️ **Important Notes**

* Confirmed tickets for both passengers.
* Original ID proof is mandatory during travel.
* Refund and TDR policies apply in case of cancellation, delay, or service failure.
* Meals available via [IRCTC eCatering](https://www.ecatering.irctc.co.in) or by calling 1323.

Let me know if you want a side-by-side comparison with the previous ticket.
}

---

**Cursor**

The output from the test run of the script `test_rag_llamaindex_with_vectordb.py` does match the details provided in your query. Here's a breakdown of the matching details:

### 🎫 **Train Ticket Overview**
- **PNR**: `2717575060` (Matches)
- **From**: Prayagraj Junction (PRYJ) (Matches)
- **To**: New Delhi (NDLS) (Matches)
- **Journey Date**: **20-Jun-2025** (Matches)
- **Departure Time**: 22:30 (20-Jun-2025) (Matches)
- **Train**: 12275 / NDLS HUMSAFAR (Matches)
- **Class**: Third AC (3A) (Matches)

### 👥 **Passengers**
- **Name**: SUCHITRA GUPTA, Age: 66, Gender: F, Booking Status: CNF/B10/9/LOWER (Matches)
- **Name**: RITA BHATACHARYA, Age: 63, Gender: F, Booking Status: CNF/B10/12/LOWER (Matches)

### 💰 **Payment Details**
- **Ticket Fare**: ₹2,310.00 (Matches)
- **IRCTC Convenience Fee (incl. GST)**: ₹23.60 (Matches)
- **Travel Insurance Premium**: ₹0.90 (Matches)
- **Total Fare**: ₹2,334.50 (Matches)

The script output provides the same information as the details you provided, confirming that the data extracted from the ticket matches the expected details. If you need a side-by-side comparison with a previous ticket, please provide the details of the previous ticket for comparison.

