# API Output Schema

This project exposes a production-friendly JSON shape for web applications, REST APIs, mobile clients, and database ingestion.

## Document Types

### Appointment

Use this schema when the document is classified as `Appointment`.

```json
{
  "status": "success",
  "document_type": "Appointment",
  "data": {
    "appointment_date": "7 สิงหาคม 2569",
    "appointment_time": "08:30 น",
    "preparation_instruction": "งดอาหารและงดน้ำ หลังเวลา 24.00 น. (หลังเที่ยงคืน)"
  },
  "error": null
}
```

Fields:
- `appointment_date`: date of the appointment
- `appointment_time`: appointment time
- `preparation_instruction`: preparation guidance before the appointment

### MedicineLabel

Use this schema when the document is classified as `MedicineLabel`.

```json
{
  "status": "success",
  "document_type": "MedicineLabel",
  "data": {
    "medicine_name": "Paracetamol TAB 500 MG (MYMOL)",
    "usage_instruction": "รับประทานครั้งละ 1 เม็ด ทุก 4-6 ชั่วโมง เวลามีไข้ หรือมีอาการปวดหัว"
  },
  "error": null
}
```

Fields:
- `medicine_name`: medicine name
- `usage_instruction`: usage instructions for the medicine

## Contract Notes

- `data` only contains fields relevant to the detected document type
- debug-only fields are intentionally excluded
- JSON is emitted with `ensure_ascii=False` for Thai text support
- `error` is `null` on success and contains a short message on failure

## Recommended Consumer Behavior

- Treat `status != "success"` as a failed request
- Read `document_type` before mapping fields into your frontend model
- Do not expect `raw_text`, `text_regions`, `bbox`, or `classification_score` in production output
