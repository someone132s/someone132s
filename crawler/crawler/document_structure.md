# 病历文档结构分析

## 统一响应结构

所有文档类型在顶层都遵循相同的基本响应结构：

```json
{
  "code": 200,
  "data": {
    "list": [
      {
        "documentList": [
          {
            // 文档元数据
            "docName": "文档名称",
            "docCode": "文档代码",
            "documentUniqueId": "文档唯一ID",
            "patientId": "患者ID",
            "patientName": "患者姓名",
            "dicomStudyTime": "文档时间",
            "payLoadType": "文档类型",
            "payLoadTypeName": "文档类型名称",
            "filepath": "文件路径",
            // 其他文档特有字段...
          }
        ],
        // 其他列表数据...
      }
    ],
    "page": {
      // 分页信息
    }
  }
}
```

## 文档类型分类

1. **检查检验类文档** (jiancha/jianyan):
   - 包含检查部位(bodyPart)、检查方法(modality)等字段
   - 示例: 放射报告、超声报告、病理报告

2. **护理记录类文档** (hulijilu):
   - 包含护理评估、生命体征等数据
   - 数据结构更复杂，有嵌套的时间序列数据

3. **病历文书类文档** (bingchengjilu/ruyuanjilu/chuyuanjilu):
   - 包含入院记录、出院记录等完整病历
   - 有固定的文书模板结构

4. **医嘱类文档** (yizhu):
   - 包含医嘱执行记录
   - 有时间、执行人、状态等信息

## 数据库设计建议

基于统一结构设计文档表：

```sql
CREATE TABLE medical_documents (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(100) UNIQUE NOT NULL,  -- documentUniqueId
    patient_id VARCHAR(50) NOT NULL,  -- patientId
    visit_flow_id VARCHAR(100),  -- visitFlowId
    doc_type VARCHAR(50) NOT NULL,  -- payLoadType
    doc_name VARCHAR(100) NOT NULL,  -- docName
    doc_time TIMESTAMP,  -- dicomStudyTime
    file_path TEXT,  -- filepath/pdfPath
    raw_data JSONB NOT NULL,  -- 原始文档数据
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 为常用查询字段创建索引
CREATE INDEX idx_document_patient ON medical_documents(patient_id);
CREATE INDEX idx_document_visit ON medical_documents(visit_flow_id);
CREATE INDEX idx_document_type ON medical_documents(doc_type);
CREATE INDEX idx_document_time ON medical_documents(doc_time);
```

## Scrapy Pipeline处理建议

1. 统一解析器处理所有文档类型的公共字段
2. 按payLoadType分发到不同的细化处理器
3. 最终统一存储到medical_documents表
4. 特殊文档类型可提取关键字段到专用表
