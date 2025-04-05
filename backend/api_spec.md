# 医疗助手系统API规范

## 基础信息
- 协议: HTTP/HTTPS
- 数据格式: JSON
- 认证方式: JWT (后期添加)
- 基础路径: /api/v1

## 患者管理接口
`GET /patients` - 获取患者列表
`POST /patients` - 创建新患者
`GET /patients/{id}` - 获取患者详情
`PUT /patients/{id}` - 更新患者信息
`DELETE /patients/{id}` - 删除患者

## 病历管理接口
`GET /patients/{id}/records` - 获取患者病历
`POST /patients/{id}/records` - 添加病历记录
`GET /records/{id}` - 获取病历详情
`PUT /records/{id}` - 更新病历

## 数据格式示例
```json
{
  "patient": {
    "id": 1,
    "name": "张三",
    "gender": "男",
    "age": 45,
    "created_at": "2025-03-28T10:20:00Z"
  },
  "medical_record": {
    "id": 1,
    "patient_id": 1,
    "diagnosis": "高血压",
    "treatment": "降压药",
    "created_at": "2025-03-28T10:25:00Z"
  }
}
```

## 错误响应
```json
{
  "error": {
    "code": 404,
    "message": "患者不存在"
  }
}
