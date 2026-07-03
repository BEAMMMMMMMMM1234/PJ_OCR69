## Evaluation

Sprint 6 เพิ่มระบบประเมินผล 2 ส่วน:

1. `OCR Recognition CER` ใช้ Levenshtein distance
2. `Information Extraction Field Accuracy` เปรียบเทียบ `final_data` ของ ground truth กับ prediction

### เตรียม Ground Truth

สร้างไฟล์ `evaluation/sample_ground_truth.json` ตามโครงสร้างนี้:

```json
{
  "samples": [
    {
      "image_path": "data/test_images/A1.jpg",
      "document_type": "Appointment",
      "reference_text": "ข้อความจริงทั้งหมดที่ควรอ่านได้จากเอกสาร",
      "ground_truth_final_data": {
        "appointment_date": "7 สิงหาคม 2569",
        "appointment_time": "08:30 น",
        "preparation_instruction": "งดอาหารและงดน้ำ หลังเวลา 24.00 น. (หลังเที่ยงคืน)"
      }
    }
  ]
}
```

### วิธีรัน

```bash
python evaluation/evaluate.py
```

ระบบจะอ่าน `evaluation/sample_ground_truth.json`, รัน pipeline กับแต่ละภาพ และบันทึกรายงานลง `evaluation/evaluation_report.json`

### CER

CER หรือ Character Error Rate คำนวณจาก Levenshtein distance ระหว่าง `reference_text` กับ OCR text ที่ทำนายได้

- normalize ด้วย `strip`
- รวม whitespace หลายตัวให้เป็นช่องว่างเดียว
- สูตรคือ `edit_distance / len(reference_text)`
- ถ้า reference ว่างและ predicted ว่าง ให้ได้ `0.0`
- ถ้า reference ว่างแต่ predicted ไม่ว่าง ให้ได้ `1.0`

### Field Accuracy

Field Accuracy เปรียบเทียบ `ground_truth_final_data` กับ `predicted final_data`

- เทียบเฉพาะ field ที่มีใน ground truth
- normalize ด้วย `strip`
- รวม whitespace หลายตัวให้เป็นช่องว่างเดียว
- รายงานผลราย field และค่า accuracy รวม

### หมายเหตุ

- ใช้ `ensure_ascii=False`
- รองรับภาษาไทย
- ไม่แก้ pipeline หลัก
- ผลลัพธ์ถูกบันทึกเป็น JSON
