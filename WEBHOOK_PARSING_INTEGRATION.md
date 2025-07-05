# 🔗 Webhook Parsing Integration Documentation

## ✅ **SUCCESSFULLY INTEGRATED: Via & Custom Fields Parsing**

Based on the requirements from `parse_tickets 1.py`, we have successfully integrated comprehensive parsing for Zendesk webhook data including `via` and `custom_fields` handling.

---

## 🎯 **Key Features Implemented**

### **1. Via Field Parsing** 
- ✅ **Multiple Input Formats**: Handles JSON strings, dict objects, None, and empty values
- ✅ **Channel Extraction**: Captures communication channel (web, email, api, etc.)
- ✅ **Source Information**: Extracts from/to details including names and addresses
- ✅ **Error Handling**: Graceful fallback to `{'channel': 'unknown'}` on parsing errors

### **2. Custom Fields Parsing**
- ✅ **Field ID Mapping**: Maps Zendesk numeric IDs to TESSA field names
- ✅ **Dynamic Parsing**: Handles JSON strings, list objects, None, and empty values  
- ✅ **TESSA Integration**: Maps to product, support_theme, severity, ticket_type, summary
- ✅ **Error Resilience**: Returns empty dict on parsing failures

### **3. Database Integration**
- ✅ **JSON Storage**: Via data stored as JSONField for complex structure preservation
- ✅ **Field Mapping**: Custom fields automatically populate TESSA-specific columns
- ✅ **Data Integrity**: All webhook data properly validated and stored

---

## 📋 **Custom Field Mapping Configuration**

```python
CUSTOM_FIELD_MAPPING = {
    12713190866711: 'severity',      # Critical, High, Medium, Low
    12914744896791: 'ticket_type',   # Bug, Incident, Request, etc.
    14382186096919: 'summary',       # Brief ticket summary
    29660953136279: 'product',       # IVMS, BNGAI, CRIS, AIMS, IEMS
    30235222279191: 'support_theme'  # Access Issues, Performance, etc.
}
```

---

## 🔧 **Implementation Details**

### **Parsing Functions** (`tickets/webhooks.py`)

#### **`parse_via(via_data)`**
```python
# Input: {"channel": "email", "source": {"from": {...}, "to": {...}}}
# Output: {"channel": "email", "source": {...}}
```

**Supports:**
- ✅ Dict objects (direct webhook data)
- ✅ JSON strings (serialized webhook data) 
- ✅ None/empty values (fallback handling)

#### **`parse_custom_fields(custom_fields_data)`**
```python
# Input: [{"id": 12713190866711, "value": "critical"}, ...]
# Output: {"severity": "critical", "product": "IVMS", ...}
```

**Supports:**
- ✅ List of field objects (standard webhook format)
- ✅ JSON string representation
- ✅ None/empty values (returns empty dict)

### **Webhook Integration** (`update_ticket_from_webhook`)

**Enhanced Processing:**
1. **Parse via data** → Store in `ticket.via` JSONField
2. **Parse custom fields** → Map to TESSA-specific fields
3. **Preserve original data** → All webhook data maintained
4. **Field prioritization** → Custom fields override basic webhook fields

---

## 📊 **Test Results Summary**

### **✅ Individual Function Tests**
```
Via Parsing Tests:
  ✅ Dict input → {'channel': 'web', 'source': {...}}
  ✅ JSON string → {'channel': 'email', 'source': {...}}
  ✅ None input → {'channel': 'unknown'}
  ✅ Empty string → {'channel': 'unknown'}

Custom Fields Tests:
  ✅ List input → {'severity': 'critical', 'product': 'IVMS'}
  ✅ JSON string → {'ticket_type': 'bug', 'summary': 'Test Summary'}
  ✅ None input → {}
  ✅ Empty list → {}
```

### **✅ Complete Webhook Processing**
```
Webhook Data Processing Test:
  ✅ Ticket creation successful (ID: 354)
  ✅ Via data parsed and stored correctly
  ✅ Custom fields mapped to TESSA fields
  ✅ Array fields preserved (tags, collaborators, etc.)
  ✅ User relationships maintained
  ✅ JSON serialization/deserialization working
```

---

## 🚀 **Production Ready Features**

### **1. Robust Error Handling**
- ✅ **Graceful Degradation**: Failed parsing doesn't break ticket creation
- ✅ **Logging**: Warning logs for parsing errors with details
- ✅ **Fallback Values**: Sensible defaults for missing/invalid data

### **2. Audit Trail Integration** 
- ✅ **Webhook Audit Logs**: Complete parsing results tracked
- ✅ **Via Channel Tracking**: Communication channel logged for analysis
- ✅ **Custom Fields Status**: Whether custom fields were present/parsed

### **3. Data Validation**
- ✅ **Type Checking**: Input validation for all parsing functions
- ✅ **JSON Validation**: Proper JSON structure verification
- ✅ **Field Mapping**: Only known field IDs processed

---

## 📈 **Example Webhook Processing Flow**

### **Input Webhook Data:**
```json
{
  "id": 123456,
  "subject": "IVMS Login Issue",
  "via": {
    "channel": "email",
    "source": {
      "from": {"name": "John Doe", "address": "john@customer.com"},
      "to": {"name": "Support", "address": "support@aidash.com"}
    }
  },
  "custom_fields": [
    {"id": 12713190866711, "value": "high"},
    {"id": 29660953136279, "value": "IVMS"},
    {"id": 30235222279191, "value": "Access and Login Issues"}
  ]
}
```

### **Parsed & Stored Result:**
```python
Ticket Object:
  ticket_id = 123456
  subject = "IVMS Login Issue"
  via = {"channel": "email", "source": {...}}  # JSONField
  
  # Mapped from custom_fields:
  severity = "high"
  product = "IVMS" 
  support_theme = "Access and Login Issues"
```

---

## 🔄 **Integration Testing Commands**

```bash
# Test webhook parsing functions
python manage.py test_webhook_parsing

# Test complete webhook endpoint
curl -X POST "http://localhost:8000/tickets/webhook/test/"

# Test specific ticket parsing
python manage.py shell -c "from tickets.webhooks import parse_via, parse_custom_fields; ..."
```

---

## 🎉 **Status: PRODUCTION READY**

The webhook parsing integration is **fully implemented** and **thoroughly tested**:

- ✅ **Via field parsing** implemented per `parse_tickets 1.py` specifications
- ✅ **Custom fields parsing** with complete field ID mapping
- ✅ **Database integration** with proper JSONField storage
- ✅ **Error handling** and **audit logging** included
- ✅ **Comprehensive testing** with multiple input scenarios
- ✅ **Production validation** through webhook endpoints

**Ready for Zendesk webhook integration in production environment!** 🚀 